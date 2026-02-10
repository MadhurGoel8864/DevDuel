"""User Data Access Object"""

import logging
from typing import Optional
from datetime import date

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def create(self, email: str, full_name: str, dob :date, password_hash: str) -> User:
        """
        Create a new user in the database.

        Args:
            email (str): User's email address.
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
                full_name=full_name,
                password_hash=password_hash,
                is_verified=False,
                dob=dob,
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

    async def verify_user(self, email: str) -> Optional[User]:
        """
        Verify a user by setting is_verified to True.

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
                full_name=full_name,
                password_hash=None,
                auth_provider=provider,
                provider_user_id=provider_user_id,
                is_verified=True,
                is_active=True,
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
        Update user's password hash.

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
            await self._session.commit()
            await self._session.refresh(user)
            return user
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update password for user {user_id}: {e}")
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
