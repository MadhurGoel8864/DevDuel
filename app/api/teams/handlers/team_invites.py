"""Team Invite Handlers"""

import logging

from fastapi import BackgroundTasks, Body, Depends, Path, Query

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.teams.schemas.team_invites import (
    InviteAcceptRequest,
    InviteDeclineRequest,
    InviteMemberRequest,
    InviteResponse,
    InviteValidateResponse,
)
from app.api.teams.services.team_invites import (
    TeamInviteService,
    get_team_invite_service,
)
from app.services.email import email_service
from app.services.email.templates.team_invite import (
    team_invite_new_user_template,
    team_invite_registered_template,
)

logger = logging.getLogger(__name__)


# ── Background email tasks ─────────────────────────────────────────────────────


def _send_registered_user_invite(
    email: str,
    team_name: str,
    role: str,
    accept_url: str,
    decline_url: str,
    inviter_email: str,
    inviter_name: str | None,
    invitee_name: str | None,
) -> None:
    """Background task — invite email for an already-registered user."""
    try:
        subject, html_body = team_invite_registered_template(
            team_name=team_name,
            role=role,
            accept_url=accept_url,
            decline_url=decline_url,
            inviter_email=inviter_email,
            inviter_name=inviter_name,
            invitee_name=invitee_name,
        )
        email_service.send_email(
            to_email=email, subject=subject, body=html_body, html=True
        )
        logger.info(f"Registered-user invite email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send registered-user invite email to {email}: {e}")


def _send_new_user_invite(
    email: str,
    team_name: str,
    role: str,
    register_url: str,
    inviter_email: str,
    inviter_name: str | None,
    invitee_name: str | None,
) -> None:
    """Background task — invite email for a new (unregistered) user."""
    try:
        subject, html_body = team_invite_new_user_template(
            team_name=team_name,
            role=role,
            register_url=register_url,
            inviter_email=inviter_email,
            inviter_name=inviter_name,
            invitee_name=invitee_name,
        )
        email_service.send_email(
            to_email=email, subject=subject, body=html_body, html=True
        )
        logger.info(f"New-user invite email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send new-user invite email to {email}: {e}")


# ── Handlers ───────────────────────────────────────────────────────────────────


async def send_invite_handler(
    team_id: str = Path(..., description="Team ID"),
    request: InviteMemberRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserWithPermissions = Depends(get_current_user),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
) -> InviteResponse:
    """
    Send a team membership invite to an email address.
    Creator-only. Works for both registered and unregistered users.
    Email is sent as a background task so the response is immediate.
    """
    result = await invite_service.send_invite(
        team_id=team_id,
        email=request.data.email,
        role=request.data.role,
        requesting_user_id=current_user.user_id,
        invitee_name=request.data.name,
    )

    if result["is_new_user"]:
        background_tasks.add_task(
            _send_new_user_invite,
            email=result["email"],
            team_name=result["team_name"],
            role=result["role"],
            register_url=result["register_url"],
            inviter_email=result["inviter_email"],
            inviter_name=result["inviter_name"],
            invitee_name=result["invitee_name"],
        )
    else:
        background_tasks.add_task(
            _send_registered_user_invite,
            email=result["email"],
            team_name=result["team_name"],
            role=result["role"],
            accept_url=result["accept_url"],
            decline_url=result["decline_url"],
            inviter_email=result["inviter_email"],
            inviter_name=result["inviter_name"],
            invitee_name=result["invitee_name"],
        )

    return InviteResponse(
        message=f"Invite sent to {result['email']}",
        is_new_user=result["is_new_user"],
    )


async def validate_invite_handler(
    token: str = Query(..., description="Invite token from email link"),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
) -> InviteValidateResponse:
    """
    Validate an invite token.
    No authentication required — user may not be logged in yet.
    Frontend calls this when the invite link is opened to decide
    which page to render (accept vs register).
    """
    result = await invite_service.validate_token(token)
    return InviteValidateResponse(**result)


async def accept_invite_handler(
    request: InviteAcceptRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
) -> InviteResponse:
    """
    Accept a team invite. Registered + authenticated users only.
    The authenticated user's email must match the invite email.
    """
    await invite_service.accept_invite(
        token=request.data.token,
        requesting_user_id=current_user.user_id,
    )
    return InviteResponse(message="Invite accepted. You have been added to the team.")


async def decline_invite_handler(
    request: InviteDeclineRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
) -> InviteResponse:
    """
    Decline a team invite. Both Redis keys are deleted immediately.
    """
    await invite_service.decline_invite(
        token=request.data.token,
        requesting_user_id=current_user.user_id,
    )
    return InviteResponse(message="Invite declined.")
