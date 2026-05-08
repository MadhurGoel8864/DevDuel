# app/workers/tasks/email.py
"""ARQ tasks for durable email delivery.

Replaces FastAPI BackgroundTasks (in-process, lost on crash) with a
Redis-backed queue that survives restarts and supports retries.

smtplib.SMTP is synchronous, so each task wraps it in run_in_executor
to avoid blocking the ARQ worker's event loop.
"""
import asyncio
import logging
from functools import partial

from app.services.email import email_service
from app.services.email.templates import otp_email_template, password_reset_email_template
from app.services.email.templates.contest_update import contest_update_template
from app.services.email.templates.team_invite import (
    team_invite_new_user_template,
    team_invite_registered_template,
)
from app.services.email.templates.team_join_request import (
    team_join_request_accepted_template,
    team_join_request_leader_template,
)

logger = logging.getLogger(__name__)


async def send_otp_email_task(ctx: dict, email: str, otp: str) -> None:
    """Send OTP verification email."""
    subject, html_body = otp_email_template(otp)
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, email, subject, html_body, True),
    )
    logger.info(f"[task:email] OTP sent to {email}")


async def send_password_reset_task(ctx: dict, email: str, reset_link: str) -> None:
    """Send password reset email."""
    subject, html_body = password_reset_email_template(reset_link)
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, email, subject, html_body, True),
    )
    logger.info(f"[task:email] password reset sent to {email}")


async def send_team_invite_task(
    ctx: dict,
    email: str,
    is_new_user: bool,
    team_name: str,
    role: str,
    inviter_email: str,
    inviter_name: str | None = None,
    invitee_name: str | None = None,
    # registered user fields
    accept_url: str | None = None,
    decline_url: str | None = None,
    # new user fields
    register_url: str | None = None,
) -> None:
    """Send team invite email to a registered or new user."""
    if is_new_user:
        subject, html_body = team_invite_new_user_template(
            team_name=team_name,
            role=role,
            register_url=register_url,
            inviter_email=inviter_email,
            inviter_name=inviter_name,
            invitee_name=invitee_name,
        )
    else:
        subject, html_body = team_invite_registered_template(
            team_name=team_name,
            role=role,
            accept_url=accept_url,
            decline_url=decline_url,
            inviter_email=inviter_email,
            inviter_name=inviter_name,
            invitee_name=invitee_name,
        )
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, email, subject, html_body, True),
    )
    logger.info(f"[task:email] team invite sent to {email} (new_user={is_new_user})")


async def send_join_request_leader_task(
    ctx: dict,
    leader_email: str,
    team_name: str,
    role: str,
    manage_url: str,
    requester_email: str,
    leader_name: str | None = None,
    requester_name: str | None = None,
) -> None:
    """Notify the team leader about a new join request."""
    subject, html_body = team_join_request_leader_template(
        leader_name=leader_name,
        team_name=team_name,
        requester_name=requester_name,
        requester_email=requester_email,
        role=role,
        manage_url=manage_url,
    )
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, leader_email, subject, html_body, True),
    )
    logger.info(f"[task:email] join request leader notification sent to {leader_email}")


async def send_join_request_accepted_task(
    ctx: dict,
    requester_email: str,
    team_name: str,
    role: str,
    team_url: str,
    requester_name: str | None = None,
) -> None:
    """Notify the requester that their join request was accepted."""
    subject, html_body = team_join_request_accepted_template(
        requester_name=requester_name,
        team_name=team_name,
        role=role,
        team_url=team_url,
    )
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, requester_email, subject, html_body, True),
    )
    logger.info(f"[task:email] join request accepted notification sent to {requester_email}")


async def send_contest_update_task(
    ctx: dict,
    email: str,
    contest_name: str,
    diff: dict,
) -> None:
    """Send a contest update notification to a single registered user."""
    subject, html_body = contest_update_template(
        contest_name=contest_name,
        diff=diff,
    )
    await asyncio.get_event_loop().run_in_executor(
        None,
        partial(email_service.send_email, email, subject, html_body, True),
    )
    logger.info(f"[task:email] contest update sent to {email}")
