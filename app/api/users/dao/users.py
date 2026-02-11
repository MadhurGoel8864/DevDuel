"""User Data Access Object"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common.user_utils import generate_username_from_email
from app.core.database import get_db
from app.database.models.users import User

logger = logging.getLogger(__name__)


class UserDAO:
    """Data Access Object for User model."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the DAO with a database session.

        Args:
            session (AsyncSession): SQLAlchemy async session for database operations.
        """
        self._session = session

    async def generate_unique_username(self, email: str) -> str:
        """
        Generate a unique username from email address.

        If base username exists, adds random 4-digit suffix.
        Retries up to 5 times with different random suffixes.

        Args:
            email: User's email address

        Returns:
            Unique username

        Raises:
            ValueError: If unable to generate unique username after retries
        """
        base_username = generate_username_from_email(email)

        # First try the base username
        existing_user = await self.get_by_username(base_username)
        if not existing_user:
            return base_username

        # Try with random suffixes
        max_retries = 5
        for _ in range(max_retries):
            # Generate random 4-digit suffix
            suffix = secrets.randbelow(10000)
            candidate = f"{base_username}_{suffix:04d}"

            # Ensure it fits in 50 characters
            if len(candidate) > 50:
                # Truncate base username to make room for suffix
                truncated_base = base_username[: 50 - 6]  # 6 chars for _XXXX
                candidate = f"{truncated_base}_{suffix:04d}"

            existing_user = await self.get_by_username(candidate)
            if not existing_user:
                return candidate

        # If all retries failed, raise error
        raise ValueError(
            f"Unable to generate unique username from email '{email}' after {max_retries} attempts"
        )

    async def create(
        self, email: str, username: str, full_name: str, password_hash: str
    ) -> User:
        """
        Create a new user in the database.

        Args:
            email (str): User's email address.
            username (str): User's unique username.
            full_name (str): User's full name.
            password_hash (str): Hashed password for the user.

        Returns:
            User: The created user instance.

        Raises:
            Exception: If database operation fails.
        """
        try:
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                password_hash=password_hash,
                is_verified=False,
            )
            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Exception occurred while creating user: {e}")
            raise e

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id (int): User ID to retrieve.

        Returns:
            Optional[User]: User instance if found, None otherwise.
        """
        try:
            result = await self._session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Exception occurred while getting user by id: {e}")
            raise e

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email (str): Email address to search for.

        Returns:
            Optional[User]: User instance if found, None otherwise.
        """
        try:
            result = await self._session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Exception occurred while getting user by email: {e}")
            raise e

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username (str): Username to search for.

        Returns:
            Optional[User]: User instance if found, None otherwise.
        """
        try:
            result = await self._session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Exception occurred while getting user by username: {e}")
            raise e

    async def verify_user(self, email: str) -> Optional[User]:
        """
        Verify a user by setting is_verified to True and email_verified_at timestamp.

        Args:
            email (str): Email address of the user to verify.

        Returns:
            Optional[User]: Updated user instance if found, None otherwise.

        Raises:
            Exception: If database operation fails.
        """
        try:
            # Get the user by email
            user = await self.get_by_email(email)
            if user:
                user.is_verified = True
                user.email_verified_at = datetime.now(timezone.utc)
                await self._session.commit()
                await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Exception occurred while verifying user: {e}")
            raise e

    # Remove
    async def get_all(self) -> list[User]:
        """
        Get all users.

        Returns:
            list[User]: List of all user instances.
        """
        try:
            result = await self._session.execute(select(User))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Exception occurred while getting all users: {e}")
            raise e

    async def link_oauth_provider(
        self,
        user: User,
        provider: str,
        provider_user_id: str,
    ) -> User:
        """
        Link an existing user account with an OAuth provider.
        Used when a local/OTP user logs in via Google.
        """
        try:
            user.auth_provider = provider
            user.provider_user_id = provider_user_id
            user.is_verified = True  # OAuth email is verified

            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to link OAuth provider: {e}")
            raise e

    async def create_oauth_user(
        self,
        email: str,
        username: str,
        full_name: str | None,
        provider: str,
        provider_user_id: str,
    ) -> User:
        """
        Create a new user via OAuth (Google).
        """
        try:
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                password_hash=None,
                auth_provider=provider,
                provider_user_id=provider_user_id,
                is_verified=True,
                is_active=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create OAuth user: {e}")
            raise e

    async def update_password(self, user_id: str, new_password_hash: str) -> User:
        """
        Update user's password hash and password_updated_at timestamp.

        Args:
            user_id (str): User ID to update.
            new_password_hash (str): New hashed password.

        Returns:
            User: Updated user instance.

        Raises:
            Exception: If database operation fails or user not found.
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.password_hash = new_password_hash
            user.password_updated_at = datetime.now(timezone.utc)
            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update password for user {user_id}: {e}")
            raise e

    async def update_last_login(self, user_id: str) -> User:
        """
        Update user's last_login_at timestamp.

        Args:
            user_id (str): User ID to update.

        Returns:
            User: Updated user instance.

        Raises:
            Exception: If database operation fails or user not found.
        """

        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.last_login_at = datetime.now(timezone.utc)
            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            raise e


# Dependency
async def get_user_dao(session: AsyncSession = Depends(get_db)) -> UserDAO:
    """
    FastAPI dependency to provide a UserDAO instance.

    Args:
        session (AsyncSession, optional): Database session injected via dependency.

    Returns:
        UserDAO: DAO instance ready to use.
    """
    return UserDAO(session)
