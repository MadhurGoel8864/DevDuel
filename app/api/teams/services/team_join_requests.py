"""Team Join Request Service Layer"""

import logging
from typing import Any

from fastapi import Depends

from app.api.teams.dao.teams import (
    TeamDAO,
    TeamJoinRequestDAO,
    TeamMemberDAO,
    get_team_dao,
    get_team_join_request_dao,
    get_team_member_dao,
)
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.config import settings
from app.core.enums import JoinRequestStatus, TeamRole
from app.core.exceptions.teams import (
    CannotRequestOwnTeamException,
    JoinRequestAlreadyPendingException,
    JoinRequestAlreadyResolvedException,
    JoinRequestNotFoundException,
    JoinRequestPermissionDeniedException,
    NotTeamCreatorException,
    TeamHasNoOpenSlotsException,
    TeamMemberAlreadyExistsException,
    TeamNotFoundException,
)
from app.database.models.teams import TeamJoinRequest

logger = logging.getLogger(__name__)


class TeamJoinRequestService:
    """Business logic for self-initiated team join requests."""

    def __init__(
        self,
        team_dao: TeamDAO,
        member_dao: TeamMemberDAO,
        user_dao: UserDAO,
        request_dao: TeamJoinRequestDAO,
    ):
        self._team_dao = team_dao
        self._member_dao = member_dao
        self._user_dao = user_dao
        self._request_dao = request_dao

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _open_roles_for_team(self, team_id: str) -> list[TeamRole]:
        """Return the list of TeamRole values that are still unfilled in the team."""
        open_roles: list[TeamRole] = []
        for role in (TeamRole.BIDDING, TeamRole.CODING):
            count = await self._member_dao.count_by_role(team_id=team_id, role=role)
            if count == 0:
                open_roles.append(role)
        return open_roles

    async def _serialize_request(self, req: TeamJoinRequest) -> dict[str, Any]:
        """Project a TeamJoinRequest + its loaded relationships into a flat dict."""
        team = req.team
        user = req.user
        return {
            "id": req.id,
            "team_id": req.team_id,
            "team_name": team.name if team else None,
            "user_id": req.user_id,
            "requester_username": user.username if user else None,
            "requester_email": user.email if user else None,
            "role": req.role,
            "status": req.status,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
        }

    # ── Public methods ─────────────────────────────────────────────────────────

    async def browse_teams(
        self, user_id: str, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated browseable teams (excluding ones the user is in)."""
        teams, total = await self._team_dao.get_browseable_for_user(
            user_id=user_id, limit=limit, offset=offset
        )

        # Pre-fetch creator usernames to avoid N+1
        creator_ids = list({t.created_by for t in teams})
        creators = {}
        for cid in creator_ids:
            u = await self._user_dao.get_by_id(cid)
            if u:
                creators[cid] = u.username

        items: list[dict[str, Any]] = []
        for t in teams:
            members = list(t.members) if t.members else []
            existing_roles = {m.role for m in members}
            open_roles = [
                r for r in (TeamRole.BIDDING, TeamRole.CODING) if r not in existing_roles
            ]
            items.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "creator_username": creators.get(t.created_by),
                    "member_count": len(members),
                    "is_open": len(open_roles) > 0,
                    "open_roles": open_roles,
                    "created_at": t.created_at,
                }
            )
        return items, total

    async def send_request(self, user_id: str, team_id: str) -> dict[str, Any]:
        """Send a join request. Auto-assigns the role based on what's open.

        Raises:
            TeamNotFoundException, CannotRequestOwnTeamException,
            TeamMemberAlreadyExistsException, JoinRequestAlreadyPendingException,
            TeamHasNoOpenSlotsException
        """
        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)

        if team.created_by == user_id:
            raise CannotRequestOwnTeamException(team_id=team_id)

        existing_member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if existing_member:
            raise TeamMemberAlreadyExistsException(user_id=user_id, team_id=team_id)

        existing_pending = await self._request_dao.get_pending_for_user(user_id)
        if existing_pending:
            raise JoinRequestAlreadyPendingException(team_id=existing_pending.team_id)

        open_roles = await self._open_roles_for_team(team_id)
        if not open_roles:
            raise TeamHasNoOpenSlotsException(team_id=team_id)

        # Auto-assign: prefer CODING when both are open
        assigned_role = TeamRole.CODING if TeamRole.CODING in open_roles else open_roles[0]

        req = await self._request_dao.create(
            team_id=team_id, user_id=user_id, role=assigned_role
        )

        # Fetch leader + requester info for the email
        leader = await self._user_dao.get_by_id(team.created_by)
        requester = await self._user_dao.get_by_id(user_id)

        manage_url = f"{settings.FRONTEND_BASE_URL}/teams/{team_id}"

        return {
            "request_id": req.id,
            "team_id": team_id,
            "team_name": team.name,
            "role": assigned_role.value,
            "leader_email": leader.email if leader else None,
            "leader_name": leader.username if leader else None,
            "requester_name": requester.username if requester else None,
            "requester_email": requester.email if requester else None,
            "manage_url": manage_url,
        }

    async def list_for_team(
        self, team_id: str, requesting_user_id: str
    ) -> list[dict[str, Any]]:
        """Leader-only list of pending requests for a team."""
        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        requests = await self._request_dao.get_pending_for_team(team_id)
        # team relationship not loaded by get_pending_for_team — inject team name
        result: list[dict[str, Any]] = []
        for r in requests:
            r.team = team  # type: ignore[assignment]
            result.append(await self._serialize_request(r))
        return result

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """Requester's own join request history (all statuses)."""
        requests = await self._request_dao.get_all_for_user(user_id)
        return [await self._serialize_request(r) for r in requests]

    async def accept(
        self, team_id: str, request_id: str, requesting_user_id: str
    ) -> dict[str, Any]:
        """Accept a pending request, add member, fire requester email.

        Raises:
            JoinRequestNotFoundException, NotTeamCreatorException,
            JoinRequestAlreadyResolvedException,
            TeamMemberAlreadyExistsException, TeamHasNoOpenSlotsException
        """
        req = await self._request_dao.get_by_id(request_id)
        if not req or req.team_id != team_id:
            raise JoinRequestNotFoundException(request_id=request_id)

        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        if req.status != JoinRequestStatus.PENDING:
            raise JoinRequestAlreadyResolvedException(status=req.status.value)

        # Re-check member uniqueness (race-condition safety)
        already_member = await self._member_dao.get(
            team_id=team_id, user_id=req.user_id
        )
        if already_member:
            # Mark as accepted (idempotent) and skip adding
            await self._request_dao.update_status(req, JoinRequestStatus.ACCEPTED)
            raise TeamMemberAlreadyExistsException(
                user_id=req.user_id, team_id=team_id
            )

        # Re-check the requested role is still open
        role_count = await self._member_dao.count_by_role(team_id=team_id, role=req.role)
        if role_count > 0:
            # Try to fall back to the other role if it's still open
            other_role = (
                TeamRole.BIDDING if req.role == TeamRole.CODING else TeamRole.CODING
            )
            other_count = await self._member_dao.count_by_role(
                team_id=team_id, role=other_role
            )
            if other_count > 0:
                raise TeamHasNoOpenSlotsException(team_id=team_id)
            req.role = other_role  # reassign on accept

        # Add member + flip status + cancel siblings
        await self._member_dao.add(
            team_id=team_id, user_id=req.user_id, role=req.role
        )
        await self._request_dao.update_status(req, JoinRequestStatus.ACCEPTED)
        await self._request_dao.cancel_other_pending_for_user(
            user_id=req.user_id, except_request_id=req.id
        )

        requester = req.user or await self._user_dao.get_by_id(req.user_id)
        team_url = f"{settings.FRONTEND_BASE_URL}/teams/{team_id}"

        logger.info(
            f"Join request {req.id} accepted: user {req.user_id} → team {team_id} "
            f"as {req.role.value}"
        )

        return {
            "request_id": req.id,
            "team_id": team_id,
            "team_name": team.name,
            "role": req.role.value,
            "requester_email": requester.email if requester else None,
            "requester_name": requester.username if requester else None,
            "team_url": team_url,
        }

    async def reject(
        self, team_id: str, request_id: str, requesting_user_id: str
    ) -> None:
        """Leader rejects a pending request. No email sent."""
        req = await self._request_dao.get_by_id(request_id)
        if not req or req.team_id != team_id:
            raise JoinRequestNotFoundException(request_id=request_id)

        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        if req.status != JoinRequestStatus.PENDING:
            raise JoinRequestAlreadyResolvedException(status=req.status.value)

        await self._request_dao.update_status(req, JoinRequestStatus.REJECTED)
        logger.info(f"Join request {req.id} rejected by user {requesting_user_id}")

    async def cancel(self, request_id: str, requesting_user_id: str) -> None:
        """Cancel a pending request — allowed for either the requester or the team leader."""
        req = await self._request_dao.get_by_id(request_id)
        if not req:
            raise JoinRequestNotFoundException(request_id=request_id)

        if req.status != JoinRequestStatus.PENDING:
            raise JoinRequestAlreadyResolvedException(status=req.status.value)

        is_requester = req.user_id == requesting_user_id
        is_leader = False
        if not is_requester:
            team = await self._team_dao.get_by_id(req.team_id)
            is_leader = team is not None and team.created_by == requesting_user_id

        if not (is_requester or is_leader):
            raise JoinRequestPermissionDeniedException()

        await self._request_dao.update_status(req, JoinRequestStatus.CANCELLED)
        logger.info(
            f"Join request {req.id} cancelled by user {requesting_user_id} "
            f"(requester={is_requester}, leader={is_leader})"
        )


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_team_join_request_service(
    team_dao: TeamDAO = Depends(get_team_dao),
    member_dao: TeamMemberDAO = Depends(get_team_member_dao),
    user_dao: UserDAO = Depends(get_user_dao),
    request_dao: TeamJoinRequestDAO = Depends(get_team_join_request_dao),
) -> TeamJoinRequestService:
    return TeamJoinRequestService(
        team_dao=team_dao,
        member_dao=member_dao,
        user_dao=user_dao,
        request_dao=request_dao,
    )
