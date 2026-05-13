# app/workers/settings.py
"""ARQ WorkerSettings — entrypoint for the ARQ worker process.

Run with:
    poetry run arq app.workers.settings.WorkerSettings
    # or via systemd: see devduel-worker.service
"""
import logging

from arq import cron

from app.core.arq_pool import get_arq_redis_settings
from app.workers.tasks.contest_cron import auto_transition_contests, end_contest_task, start_contest_task
from app.workers.tasks.email import (
    send_contest_update_task,
    send_join_request_accepted_task,
    send_join_request_leader_task,
    send_otp_email_task,
    send_password_reset_task,
    send_team_invite_task,
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Initialize shared resources for the worker process."""
    from app.core.logging import setup_logging

    setup_logging()
    logger.info("[arq-worker] started")


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources."""
    logger.info("[arq-worker] shutdown complete")


class WorkerSettings:
    functions = [
        send_otp_email_task,
        send_password_reset_task,
        send_team_invite_task,
        send_join_request_leader_task,
        send_join_request_accepted_task,
        send_contest_update_task,
        start_contest_task,
        end_contest_task,
    ]
    cron_jobs = [
        cron(auto_transition_contests, second=0),  # runs at :00 of every minute
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_arq_redis_settings()
    max_jobs = 10
    job_timeout = 180
    keep_result = 300   # keep job results in Redis for 5 minutes
    max_tries = 3
