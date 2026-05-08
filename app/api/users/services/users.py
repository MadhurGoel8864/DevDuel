"""User Service Layer"""

import logging
from typing import Optional

from fastapi import Depends, Request

from app.api.auth.services.cache import store_user_otp
from app.api.common.utils import generate_otp
from app.api.users.dao.users import UserDAO, get_user_dao
from app.api.users.schemas.users import UserCreateData, UserUpdateData
from app.core.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    UserValidationException,
)
from app.core.exceptions.auth import UnauthorizedException
from app.core.security.password import hash_password
from app.database.models.users import User

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class to handle business logic for User operations.

    Attributes:
        _user_dao (UserDAO): DAO instance for interacting with the user database.
    """

    def __init__(self, user_dao: UserDAO):
        """
        Initialize the service with a UserDAO instance.

        Args:
            user_dao (UserDAO): DAO for performing database operations.
        """
        self._user_dao = user_dao

    async def create_user(self, user_data: UserCreateData) -> tuple[User, str]:
        """Create a new user, generate an OTP, and return (user, otp).

        The caller is responsible for enqueuing the OTP email via ARQ.

        Raises:
            UserAlreadyExistsException: If a user with this email already exists.
        """
        logger.info(f"Checking if user with email {user_data.email} already exists")
        existing_user = await self._user_dao.get_by_email(email=user_data.email)
        if existing_user:
            raise UserAlreadyExistsException(email=user_data.email)

        username = await self._user_dao.generate_unique_username(user_data.email)
        logger.info(f"Generated username: {username} for email: {user_data.email}")

        password_hash = hash_password(user_data.password)

        user = await self._user_dao.create(
            email=user_data.email,
            username=username,
            full_name=user_data.full_name,
            password_hash=password_hash,
        )

        otp = generate_otp()
        await store_user_otp(user.id, otp)
        logger.info(f"OTP generated and stored for {user.email}")

        return user, otp

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id (int): User ID to retrieve.

        Returns:
            Optional[User]: User instance if found, None otherwise.
        """
        logger.info(f"Retrieving user with id {user_id}")
        user = await self._user_dao.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return user

    # Remove
    async def get_all_users(self) -> list[User]:
        """
        Get all users.
        Retrieves all registered DevDuel users.

        Returns:
            list[User]: List of all user instances.
        """
        logger.info("Retrieving all users")
        return await self._user_dao.get_all()

    async def get_user_by_email(self, email: str):
        """
        Get user by email address.

        Args:
            email (str): User email address

        Returns:
            User: User instance

        Raises:
            UnauthorizedException: If user not found
        """
        user = await self._user_dao.get_by_email(email)
        if not user:
            logger.warning(f"User not found for email: {email}")
            raise UnauthorizedException(message="User not found")
        return user

    async def resend_otp(self, email: str) -> tuple[bool, str | None]:
        """Generate and store a fresh OTP. Returns (otp_sent, otp).

        Returns (False, None) if user is already verified.
        The caller is responsible for enqueuing the OTP email via ARQ.

        Raises:
            UnauthorizedException: If user not found.
        """
        user = await self.get_user_by_email(email)
        logger.info(f"Resending OTP for user: {user.id}")

        if user.is_verified:
            logger.info(f"User {user.id} is already verified")
            return False, None

        try:
            otp = generate_otp()
            await store_user_otp(user.id, otp)
            logger.debug(f"New OTP stored for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to generate or store OTP for user {user.id}: {e}")
            raise Exception("Failed to generate OTP. Please try again later.") from e

        return True, otp

    async def update_profile(self, user_id: str, update_data: UserUpdateData) -> User:
        """
        Update a user's full_name and/or username.

        Args:
            user_id: ID of the user to update.
            update_data: Fields to update (both optional).

        Returns:
            User: The updated user instance.

        Raises:
            UserNotFoundException: If user does not exist.
            UserValidationException: If the requested username is already taken.
        """
        user = await self._user_dao.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)

        if update_data.username is not None and update_data.username != user.username:
            existing = await self._user_dao.get_by_username(update_data.username)
            if existing:
                raise UserValidationException(
                    message=f"Username '{update_data.username}' is already taken.",
                    details={"username": update_data.username},
                )

        return await self._user_dao.update_profile(
            user_id=user_id,
            full_name=update_data.full_name,
            username=update_data.username,
        )

    async def get_or_create_oauth_user(
        self,
        email: str,
        provider: str,
        provider_user_id: str,
        full_name: str | None = None,
    ) -> User:
        """
        Get an existing user or create/link a user via OAuth.

        Rules:
        - Same email → same user
        - Local (OTP) users get upgraded to OAuth
        - OAuth users are reused
        """

        user = await self._user_dao.get_by_email(email)

        if user:
            # Case 1: Existing LOCAL/OTP user → link OAuth
            if user.auth_provider == "local":
                return await self._user_dao.link_oauth_provider(
                    user=user,
                    provider=provider,
                    provider_user_id=provider_user_id,
                )

            # Case 2: Existing OAuth user → just login
            return user

        # Case 3: First-time OAuth login → create user
        # Generate unique username from email using DAO
        username = await self._user_dao.generate_unique_username(email)
        logger.info(f"Generated username: {username} for OAuth user: {email}")

        return await self._user_dao.create_oauth_user(
            email=email,
            username=username,
            full_name=full_name,
            provider=provider,
            provider_user_id=provider_user_id,
        )


async def get_user_service(
    request: Request,
    user_dao: UserDAO = Depends(get_user_dao),
) -> UserService:
    """
    FastAPI dependency to provide a UserService instance.

    Args:
        request (Request): FastAPI request object.
        user_dao (UserDAO, optional): DAO injected via dependency..

    Returns:
        UserService: Service instance ready to use in route handlers.
    """
    return UserService(user_dao=user_dao)
