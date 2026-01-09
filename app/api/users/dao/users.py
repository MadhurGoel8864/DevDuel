"""User Data Access Object"""

import logging
from typing import Optional

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

    async def create(self, email: str, full_name: str, password_hash: str) -> User:
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
