"""User Handler Layer"""

import logging

from arq.connections import ArqRedis
from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas.auth import UserWithPermissions
from app.api.users.schemas.users import (
    UserCreateRequest,
    UserCreateResponse,
    UserCreateResponseData,
    UserGetResponse,
    UserGetResponseData,
    UserListResponse,
    UserListResponseData,
    UserUpdateRequest,
    UserUpdateResponse,
    UserUpdateResponseData,
)
from app.api.users.services.users import UserService, get_user_service
from app.core.arq_pool import get_arq_pool_dep

logger = logging.getLogger(__name__)


async def create_user_handler(
    request: UserCreateRequest = Body(..., description="User creation data"),
    user_service: UserService = Depends(get_user_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> UserCreateResponse:
    """Create a new DevDuel user and enqueue a verification OTP email."""
    user, otp = await user_service.create_user(request.data)
    await arq_pool.enqueue_job("send_otp_email_task", email=user.email, otp=otp)
    logger.info(f"User created successfully: {user.email}")
    return UserCreateResponse(data=UserCreateResponseData.model_validate(user))


async def get_user_handler(
    user_id: str = Path(..., description="User ID to retrieve"),
    user_service: UserService = Depends(get_user_service),
) -> UserGetResponse:
    """Retrieve profile information for a DevDuel user."""
    user = await user_service.get_user_by_id(user_id)
    return UserGetResponse(data=UserGetResponseData.model_validate(user))


async def update_profile_handler(
    request: UserUpdateRequest = Body(..., description="Profile fields to update"),
    current_user: UserWithPermissions = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserUpdateResponse:
    """Update the authenticated user's full_name and/or username."""
    user = await user_service.update_profile(current_user.user_id, request.data)
    logger.info(f"Profile updated for user: {user.id}")
    return UserUpdateResponse(data=UserUpdateResponseData.model_validate(user))


# Remove
async def get_users_handler(
    user_service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """Retrieve all registered DevDuel users."""
    users = await user_service.get_all_users()
    return UserListResponse(
        data=[UserListResponseData.model_validate(user) for user in users]
    )
