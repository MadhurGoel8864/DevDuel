# app/workers/tasks/contest_cron.py
"""ARQ cron task: auto-transition contests based on wall-clock time.

Runs every 60 seconds. Transitions:
  REGISTRATION_OPEN → ACTIVE  when start_time <= now
  ACTIVE            → ENDED   when end_time   <= now

Uses bulk UPDATE to avoid per-row ORM overhead.
Idempotent — safe to run on every tick even when no contests need transitioning.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.core.enums import ContestStatus
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
