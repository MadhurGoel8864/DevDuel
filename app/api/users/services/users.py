"""User Service Layer"""

from typing import Optional

from fastapi import Depends, Request

from app.api.users.dao.users import UserDAO, get_user_dao
from app.api.users.schemas.users import UserCreateData
from app.database.models.users import User


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

    async def create_user(self, user_data: UserCreateData) -> User:
        """
        Create a new user with business logic validation.
        For carpooling: validates unique email before creating user.

        Args:
            user_data (UserCreateData): Pydantic schema with user details.

        Returns:
            User: The created user instance.

        Raises:
            ValueError: If user with email already exists.
        """
        # Business logic: Check if user already exists
        existing_user = await self._user_dao.get_by_email(email=user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")

        # Delegate to DAO
        return await self._user_dao.create(
            email=user_data.email, full_name=user_data.full_name
        )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id (int): User ID to retrieve.

        Returns:
            Optional[User]: User instance if found, None otherwise.
        """
        return await self._user_dao.get_by_id(user_id)


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
