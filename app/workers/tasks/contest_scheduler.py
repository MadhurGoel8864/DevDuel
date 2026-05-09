# app/workers/tasks/contest_scheduler.py
"""Helpers to schedule and cancel per-contest ARQ deferred jobs."""
from datetime import datetime, timezone

from arq.connections import ArqRedis
from arq.jobs import Job
from redis.asyncio import Redis

_START_KEY = "contest:{contest_id}:start_job"
_END_KEY = "contest:{contest_id}:end_job"

_GRACE = 300  # seconds added to TTL past the scheduled fire time


async def schedule_contest_transitions(
    arq_pool: ArqRedis,
    redis: Redis,
    contest_id: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Enqueue deferred start/end jobs and persist their IDs in Redis.

    Uses deterministic _job_id so re-scheduling on edit replaces the prior job.
    """
    now = datetime.now(tz=timezone.utc)
    start_utc = start_time.astimezone(timezone.utc)
    end_utc = end_time.astimezone(timezone.utc)

    start_job = await arq_pool.enqueue_job(
        "start_contest_task",
        contest_id,
        _defer_until=start_utc,
        _job_id=f"contest:{contest_id}:start",
    )
    end_job = await arq_pool.enqueue_job(
        "end_contest_task",
        contest_id,
        _defer_until=end_utc,
        _job_id=f"contest:{contest_id}:end",
    )

    if start_job:
        ttl = max(int((start_utc - now).total_seconds()) + _GRACE, 60)
        await redis.set(_START_KEY.format(contest_id=contest_id), start_job.job_id, ex=ttl)

    if end_job:
        ttl = max(int((end_utc - now).total_seconds()) + _GRACE, 60)
        await redis.set(_END_KEY.format(contest_id=contest_id), end_job.job_id, ex=ttl)


async def cancel_contest_start_job(arq_pool: ArqRedis, redis: Redis, contest_id: str) -> None:
    job_id = await redis.get(_START_KEY.format(contest_id=contest_id))
    if job_id:
        await Job(job_id=job_id, redis=arq_pool).abort()
        await redis.delete(_START_KEY.format(contest_id=contest_id))


async def cancel_contest_end_job(arq_pool: ArqRedis, redis: Redis, contest_id: str) -> None:
    job_id = await redis.get(_END_KEY.format(contest_id=contest_id))
    if job_id:
        await Job(job_id=job_id, redis=arq_pool).abort()
        await redis.delete(_END_KEY.format(contest_id=contest_id))
