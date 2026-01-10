"""User Service Layer"""

import logging
from typing import Optional

from fastapi import BackgroundTasks, Depends, Request

from app.api.auth.services.cache import store_user_otp
from app.api.common.utils import generate_otp
from app.api.users.dao.users import UserDAO, get_user_dao
from app.api.users.schemas.users import UserCreateData
from app.core.exceptions import UserAlreadyExistsException, UserNotFoundException
from app.core.exceptions.auth import UnauthorizedException
from app.core.security.password import hash_password
from app.database.models.users import User
from app.services.email import email_service
from app.services.email.templates import otp_email_template

logger = logging.getLogger(__name__)


def send_verification_otp_task(email: str, otp: str) -> None:
    """
    Background task to send verification OTP email after user creation.

    Args:
        email: User's email address
        otp: The OTP code to send
    """
    try:
        subject, html_body = otp_email_template(otp)
        email_service.send_email(
            to_email=email,
            subject=subject,
            body=html_body,
            html=True,
        )
        logger.info(f"Verification OTP sent successfully to: {email}")
    except Exception as e:
        # Log error but don't crash the background task
        logger.error(f"Failed to send verification OTP to {email}: {e}")


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

    async def create_user(
        self, user_data: UserCreateData, background_tasks: BackgroundTasks
    ) -> User:
        """
        Create a new user with business logic validation.
        For carpooling: validates unique email before creating user and sends OTP.

        Args:
            user_data (UserCreateData): Pydantic schema with user details.
            background_tasks (BackgroundTasks): FastAPI background tasks for async operations.

        Returns:
            User: The created user instance.

        Raises:
            ValueError: If user with email already exists.
        """

        # Business logic: Check if user already exists
        logger.info(f"Checking if user with email {user_data.email} already exists")
        existing_user = await self._user_dao.get_by_email(email=user_data.email)
        if existing_user:
            raise UserAlreadyExistsException(email=user_data.email)

        # Hash the password before storing
        password_hash = hash_password(user_data.password)

        # Delegate to DAO
        user = await self._user_dao.create(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=password_hash,
        )

        # Generate OTP and store in Redis
        otp = generate_otp()
        await store_user_otp(user.id, otp)

        # Send verification OTP email in background (non-blocking)
        background_tasks.add_task(send_verification_otp_task, user.email, otp)
        logger.info(f"OTP email task queued for {user.email}")

        return user

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
        For carpooling: Retrieves all registered users.

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

    async def resend_otp(self, email: str, background_tasks: BackgroundTasks) -> bool:
        """
        Resend OTP to user's email.

        Validates user exists, generates new OTP, stores in Redis, and sends email.

        Args:
            email (str): User email address
            background_tasks (BackgroundTasks): FastAPI background tasks for async operations

        Returns:
            bool: True if OTP was sent, False if user is already verified

        Raises:
            UnauthorizedException: If user not found
            Exception: If OTP generation or storage fails
        """
        # Validate user exists (raises UnauthorizedException if not found)
        user = await self.get_user_by_email(email)
        logger.info(f"Resending OTP for user: {user.id}")

        if user.is_verified:
            logger.info(f"User {user.id} is already verified")
            return False

        try:
            # Generate new OTP
            otp = generate_otp()
            logger.debug(f"Generated new OTP for user {user.id}")

            # Store OTP in Redis with TTL
            await store_user_otp(user.id, otp)

        except Exception as e:
            logger.error(f"Failed to generate or store OTP for user {user.id}: {e}")
            raise Exception("Failed to generate OTP. Please try again later.") from e

        try:
            background_tasks.add_task(send_verification_otp_task, email, otp)
            logger.info(f"Resend OTP email task queued for {email}")

        except Exception as e:
            logger.error(f"Failed to queue email task for {email}: {e}")

        return True

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
        return await self._user_dao.create_oauth_user(
            email=email,
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
