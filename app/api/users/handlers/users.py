"""User Handler Layer"""

import logging

from fastapi import BackgroundTasks, Body, Depends, Path

from app.api.users.schemas.users import (UserCreateRequest, UserCreateResponse,
                                         UserCreateResponseData,
                                         UserGetResponse, UserGetResponseData,
                                         UserListResponse,
                                         UserListResponseData)
from app.api.users.services.users import UserService, get_user_service

logger = logging.getLogger(__name__)


async def create_user_handler(
    request: UserCreateRequest = Body(..., description="User creation data"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_service: UserService = Depends(get_user_service),
) -> UserCreateResponse:
    """
    Handle user creation request.
    Creates a new DevDuel user and sends a verification OTP to their email.
    """
    # Service layer handles user creation, OTP generation, storage, and email sending
    user = await user_service.create_user(request.data, background_tasks)
    logger.info(f"User created successfully: {user.email}")

    return UserCreateResponse(data=UserCreateResponseData.model_validate(user))


async def get_user_handler(
    user_id: str = Path(..., description="User ID to retrieve"),
    user_service: UserService = Depends(get_user_service),
) -> UserGetResponse:
    """
    Handle get user request.
    Retrieves profile information for a DevDuel user.
    """
    user = await user_service.get_user_by_id(user_id)
    return UserGetResponse(data=UserGetResponseData.model_validate(user))


# Remove
async def get_users_handler(
    user_service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """
    Handle get users list request.
    Retrieves all registered DevDuel users.
    """
    users = await user_service.get_all_users()
    return UserListResponse(
        data=[UserListResponseData.model_validate(user) for user in users]
    )
