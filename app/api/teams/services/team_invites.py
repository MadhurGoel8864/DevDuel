"""Team Invite Service — Redis-backed implementation"""

import json
import logging
import secrets

from fastapi import Depends
from redis.asyncio import Redis

from app.api.teams.dao.teams import (
    TeamDAO,
    TeamMemberDAO,
    get_team_dao,
    get_team_member_dao,
)
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.config import settings
from app.core.enums import TeamRole
from app.core.exceptions.teams import (
    NotTeamCreatorException,
    TeamInviteAlreadyPendingException,
    TeamInviteEmailMismatchException,
    TeamInviteInvalidException,
    TeamMemberAlreadyExistsException,
    TeamNotFoundException,
    TeamRoleTakenException,
)
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# ── Redis key helpers ──────────────────────────────────────────────────────────


def _invite_key(token: str) -> str:
    """Main invite data key. TTL = 72h."""
    return f"invite:{token}"


def _pending_key(team_id: str, email: str) -> str:
    """Duplicate-check key — one per team+email combo. TTL = 72h."""
    return f"invite:pending:{team_id}:{email.lower()}"


def _pending_join_key(user_id: str) -> str:
    """
    Stores invite token for a newly registered user who hasn't verified OTP yet.
    TTL = 24h. Consumed inside verify_otp flow.
    """
    return f"pending_team_join:{user_id}"


class TeamInviteService:
    """
    Handles all business logic for team member invitations.

    Redis keys used:
      invite:{token}                   → invite data (72h TTL)
      invite:pending:{team_id}:{email} → duplicate guard (72h TTL)
      pending_team_join:{user_id}      → new user OTP pending (24h TTL)
    """

    def __init__(
        self,
        team_dao: TeamDAO,
        member_dao: TeamMemberDAO,
        user_dao: UserDAO,
        redis: Redis,
    ):
        self._team_dao = team_dao
        self._member_dao = member_dao
        self._user_dao = user_dao
        self._redis = redis

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _get_invite_data(self, token: str) -> dict:
        """
        Fetch and parse invite data from Redis.
        Raises appropriate exception if missing.
        """
        raw = await self._redis.get(_invite_key(token))
        if not raw:
            raise TeamInviteInvalidException()
        return json.loads(raw)

    # ── Public methods ─────────────────────────────────────────────────────────

    async def send_invite(
        self,
        team_id: str,
        email: str,
        role: TeamRole,
        requesting_user_id: str,
        invitee_name: str = "",
    ) -> dict:
        """
        Send a team invite to the given email address.

        Creates two Redis keys:
          - invite:{token}                   → invite data
          - invite:pending:{team_id}:{email} → duplicate guard

        Returns dict consumed by the handler to fire the correct email template.

        Raises:
            TeamNotFoundException, NotTeamCreatorException,
            TeamRoleTakenException, TeamMemberAlreadyExistsException,
            TeamInviteAlreadyPendingException
        """
        # ── Validate team + creator ────────────────────────────────────────────
        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        # 1 -1 role for each team CODING , BIDDING
        role_count = await self._member_dao.count_by_role(team_id=team_id, role=role)
        if role_count > 0:
            raise TeamRoleTakenException(role=role.value)

        # ── Duplicate pending invite check ─────────────────────────────────────
        existing = await self._redis.get(_pending_key(team_id, email))
        if existing:
            raise TeamInviteAlreadyPendingException(email=email)

        # ── Check if email belongs to a registered user ────────────────────────
        existing_user = await self._user_dao.get_by_email(email)
        is_new_user = existing_user is None

        if existing_user:
            # Already a member?
            already_member = await self._member_dao.get(
                team_id=team_id, user_id=existing_user.id
            )
            if already_member:
                raise TeamMemberAlreadyExistsException(
                    user_id=existing_user.id, team_id=team_id
                )

        # Use provided name, fallback to DB name for registered users
        if not invitee_name and existing_user:
            invitee_name = existing_user.full_name or existing_user.username

        # ── Generate token + store in Redis ────────────────────────────────────
        token = secrets.token_urlsafe(32)

        invite_data = {
            "team_id": team_id,
            "team_name": team.name,
            "email": email.lower(),
            "role": role.value,
        }

        # Both keys share the same TTL
        ttl = settings.INVITE_EXPIRE_SECONDS

        await self._redis.setex(_invite_key(token), ttl, json.dumps(invite_data))
        await self._redis.setex(_pending_key(team_id, email), ttl, token)

        logger.info(
            f"Invite created for {email} → team {team_id} as {role.value} "
            f"(new_user={is_new_user})"
        )

        # Fetch inviter info for the email template
        inviter = await self._user_dao.get_by_id(requesting_user_id)
        inviter_email = inviter.email if inviter else "unknown"
        inviter_name = inviter.username if inviter else None

        return {
            "is_new_user": is_new_user,
            "invite_token": token,
            "team_name": team.name,
            "role": role.value,
            "email": email,
            "invitee_name": invitee_name,
            "inviter_email": inviter_email,
            "inviter_name": inviter_name,
            "accept_url": f"{settings.FRONTEND_ACCEPT_INVITE_URL}?token={token}",
            "decline_url": f"{settings.FRONTEND_DECLINE_INVITE_URL}?token={token}",
            "register_url": f"{settings.FRONTEND_REGISTER_INVITE_URL}?invite={token}",
        }

    async def validate_token(self, token: str) -> dict:
        """
        Validate an invite token and return its metadata.

        Called by the frontend when the invite link is opened.
        No authentication required.

        Returns dict with: team_id, team_name, email, role, is_new_user

        Raises:
            TeamInviteInvalidException: Token not found in Redis (expired or never existed)
        """
        data = await self._get_invite_data(token)

        existing_user = await self._user_dao.get_by_email(data["email"])

        return {
            "team_id": data["team_id"],
            "team_name": data["team_name"],
            "email": data["email"],
            "role": data["role"],
            "is_new_user": existing_user is None,
        }

    async def accept_invite(self, token: str, requesting_user_id: str) -> None:
        """
        Accept an invite — for already-registered users only.

        Validates token, checks authenticated user email matches invite email,
        adds user to team, deletes both Redis keys.

        Raises:
            TeamInviteInvalidException, TeamInviteEmailMismatchException,
            TeamMemberAlreadyExistsException, TeamRoleTakenException
        """
        data = await self._get_invite_data(token)

        # Verify the authenticated user's email matches the invite email
        user = await self._user_dao.get_by_id(requesting_user_id)
        if not user or user.email.lower() != data["email"]:
            raise TeamInviteEmailMismatchException()

        team_id = data["team_id"]
        role = TeamRole(data["role"])

        # Guard: already a member?
        already_member = await self._member_dao.get(
            team_id=team_id, user_id=requesting_user_id
        )
        if already_member:
            raise TeamMemberAlreadyExistsException(
                user_id=requesting_user_id, team_id=team_id
            )

        # Guard: role still available?
        role_count = await self._member_dao.count_by_role(team_id=team_id, role=role)
        if role_count > 0:
            raise TeamRoleTakenException(role=role.value)

        # Add to team then clean up both Redis keys
        await self._member_dao.add(
            team_id=team_id, user_id=requesting_user_id, role=role
        )
        await self._redis.delete(_invite_key(token))
        await self._redis.delete(_pending_key(team_id, data["email"]))

        logger.info(
            f"User {requesting_user_id} accepted invite → joined team {team_id}"
        )

    async def decline_invite(self, token: str, requesting_user_id: str) -> None:
        """
        Decline an invite — deletes both Redis keys immediately.

        Raises:
            TeamInviteInvalidException, TeamInviteEmailMismatchException
        """
        data = await self._get_invite_data(token)

        user = await self._user_dao.get_by_id(requesting_user_id)
        if not user or user.email.lower() != data["email"]:
            raise TeamInviteEmailMismatchException()

        await self._redis.delete(_invite_key(token))
        await self._redis.delete(_pending_key(data["team_id"], data["email"]))

        logger.info(
            f"User {requesting_user_id} declined invite for team {data['team_id']}"
        )

    async def store_pending_join(self, user_id: str, invite_token: str) -> None:
        """
        Store the invite token against a newly registered user's ID.

        Called from register_handler after user is created but before OTP is verified.
        The token is consumed in consume_pending_join() when OTP is verified.

        TTL = 24h (must verify email within 24h for team join to happen).
        """
        await self._redis.setex(
            _pending_join_key(user_id),
            settings.PENDING_JOIN_EXPIRE_SECONDS,
            invite_token,
        )
        logger.info(f"Pending team join stored for user {user_id}")

    async def consume_pending_join(self, user_id: str, verified_email: str) -> None:
        """
        Called inside verify_otp flow after user is marked as verified.

        Checks if a pending_team_join key exists for this user, and if so:
          1. Fetches the invite data from Redis
          2. Verifies email matches
          3. Adds user to team
          4. Cleans up all 3 Redis keys

        If no pending join exists, does nothing — normal OTP verification continues.
        """
        token = await self._redis.get(_pending_join_key(user_id))
        if not token:
            # Normal OTP verification — no invite involved
            return

        # Fetch invite data — may have expired in the 24h window
        raw = await self._redis.get(_invite_key(token))
        if not raw:
            # Invite expired before OTP was verified — clean up pending key
            await self._redis.delete(_pending_join_key(user_id))
            logger.warning(
                f"Invite token expired before user {user_id} verified OTP — "
                f"team join skipped"
            )
            return

        data = json.loads(raw)

        # Email safety check
        if data["email"] != verified_email.lower():
            await self._redis.delete(_pending_join_key(user_id))
            logger.error(
                f"Email mismatch on pending join for user {user_id} — "
                f"invite email: {data['email']}, verified: {verified_email}"
            )
            return

        team_id = data["team_id"]
        role = TeamRole(data["role"])

        # Add user to team
        await self._member_dao.add(team_id=team_id, user_id=user_id, role=role)

        # Clean up all 3 Redis keys
        await self._redis.delete(_invite_key(token))
        await self._redis.delete(_pending_key(team_id, data["email"]))
        await self._redis.delete(_pending_join_key(user_id))

        logger.info(
            f"New user {user_id} verified OTP → auto-joined team {team_id} as {role.value}"
        )


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_team_invite_service(
    team_dao: TeamDAO = Depends(get_team_dao),
    member_dao: TeamMemberDAO = Depends(get_team_member_dao),
    user_dao: UserDAO = Depends(get_user_dao),
    redis: Redis = Depends(get_redis_client),
) -> TeamInviteService:
    return TeamInviteService(
        team_dao=team_dao,
        member_dao=member_dao,
        user_dao=user_dao,
        redis=redis,
    )
