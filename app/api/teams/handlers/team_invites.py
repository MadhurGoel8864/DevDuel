"""Team Invite Handlers"""

import logging

from arq.connections import ArqRedis
from fastapi import Body, Depends, Path, Query

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
from app.core.arq_pool import get_arq_pool_dep

logger = logging.getLogger(__name__)


async def send_invite_handler(
    team_id: str = Path(..., description="Team ID"),
    request: InviteMemberRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> InviteResponse:
    """
    Send a team membership invite to an email address.
    Creator-only. Works for both registered and unregistered users.
    Email is enqueued via ARQ so the response is immediate and delivery is durable.
    """
    result = await invite_service.send_invite(
        team_id=team_id,
        email=request.data.email,
        role=request.data.role,
        requesting_user_id=current_user.user_id,
        invitee_name=request.data.name,
    )

    if result["is_new_user"]:
        await arq_pool.enqueue_job(
            "send_team_invite_task",
            email=result["email"],
            is_new_user=True,
            team_name=result["team_name"],
            role=result["role"],
            inviter_email=result["inviter_email"],
            inviter_name=result["inviter_name"],
            invitee_name=result["invitee_name"],
            register_url=result["register_url"],
        )
    else:
        await arq_pool.enqueue_job(
            "send_team_invite_task",
            email=result["email"],
            is_new_user=False,
            team_name=result["team_name"],
            role=result["role"],
            inviter_email=result["inviter_email"],
            inviter_name=result["inviter_name"],
            invitee_name=result["invitee_name"],
            accept_url=result["accept_url"],
            decline_url=result["decline_url"],
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
