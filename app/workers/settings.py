# app/workers/settings.py
"""ARQ WorkerSettings — entrypoint for the ARQ worker process.

Run with:
    poetry run arq app.workers.settings.WorkerSettings
    # or via systemd: see devduel-worker.service
"""
import logging

from arq import cron

from app.core.arq_pool import get_arq_redis_settings
from app.workers.tasks.contest_cron import auto_transition_contests
from app.workers.tasks.email import (
    send_contest_update_task,
    send_join_request_accepted_task,
    send_join_request_leader_task,
    send_otp_email_task,
    send_password_reset_task,
    send_team_invite_task,
)
from app.workers.tasks.submission import process_submission_task

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Initialize shared resources for the worker process."""
    from app.core.logging import setup_logging
    from app.api.submissions.services.submissions import judge0_client

    setup_logging()
    await judge0_client.init()
    ctx["judge0"] = judge0_client
    logger.info("[arq-worker] started, Judge0 client initialized")


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources."""
    from app.api.submissions.services.submissions import judge0_client

    await judge0_client.close()
    logger.info("[arq-worker] shutdown complete")


class WorkerSettings:
    functions = [
        process_submission_task,
        send_otp_email_task,
        send_password_reset_task,
        send_team_invite_task,
        send_join_request_leader_task,
        send_join_request_accepted_task,
        send_contest_update_task,
    ]
    cron_jobs = [
        cron(auto_transition_contests, second=0),  # runs at :00 of every minute
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_arq_redis_settings()
    max_jobs = 10
    job_timeout = 180   # 3 minutes — covers long Judge0 polling windows
    keep_result = 300   # keep job results in Redis for 5 minutes
    max_tries = 3
