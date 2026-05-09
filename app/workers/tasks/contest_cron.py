# app/workers/tasks/contest_cron.py
"""ARQ tasks for contest lifecycle transitions.

Cron (runs every 60 s — safety net):
  REGISTRATION_OPEN → ACTIVE  when start_time <= now
  ACTIVE            → ENDED   when end_time   <= now

Deferred per-contest tasks (precise scheduling, enqueued at creation/edit):
  start_contest_task — fires at start_time
  end_contest_task   — fires at end_time
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.core.enums import ContestStatus
from app.core.redis import get_redis
from app.database.models.contests import Contest

logger = logging.getLogger(__name__)


async def auto_transition_contests(ctx: dict) -> None:
    now = datetime.now(tz=timezone.utc)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result_active = await session.execute(
                update(Contest)
                .where(
                    Contest.status == ContestStatus.REGISTRATION_OPEN,
                    Contest.start_time <= now,
                )
                .values(status=ContestStatus.ACTIVE)
                .returning(Contest.id)
            )
            activated = [row[0] for row in result_active.fetchall()]

            result_ended = await session.execute(
                update(Contest)
                .where(
                    Contest.status == ContestStatus.ACTIVE,
                    Contest.end_time <= now,
                )
                .values(status=ContestStatus.ENDED)
                .returning(Contest.id)
            )
            ended = [row[0] for row in result_ended.fetchall()]

    if activated:
        logger.info(f"[cron:contests] activated {len(activated)} contest(s): {activated}")
    if ended:
        logger.info(f"[cron:contests] ended {len(ended)} contest(s): {ended}")


async def start_contest_task(ctx: dict, contest_id: str) -> None:
    """Deferred task: REGISTRATION_OPEN → ACTIVE at the contest's start_time."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(Contest)
                .where(
                    Contest.id == contest_id,
                    Contest.status == ContestStatus.REGISTRATION_OPEN,
                )
                .values(status=ContestStatus.ACTIVE)
            )
    redis = await get_redis()
    await redis.delete(f"contest:{contest_id}:start_job")
    logger.info(f"[sched:contests] started contest {contest_id}")


async def end_contest_task(ctx: dict, contest_id: str) -> None:
    """Deferred task: ACTIVE → ENDED at the contest's end_time."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(Contest)
                .where(
                    Contest.id == contest_id,
                    Contest.status == ContestStatus.ACTIVE,
                )
                .values(status=ContestStatus.ENDED)
            )
    redis = await get_redis()
    await redis.delete(f"contest:{contest_id}:end_job")
    logger.info(f"[sched:contests] ended contest {contest_id}")
