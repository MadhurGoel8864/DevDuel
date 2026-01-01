"""User Handler Layer"""

from fastapi import Body, Depends, Path

from app.api.users.schemas.users import (
    UserCreateRequest,
    UserCreateResponse,
    UserCreateResponseData,
    UserGetResponse,
    UserGetResponseData,
    UserListResponse,
    UserListResponseData,
)
from app.api.users.services.users import UserService, get_user_service


async def create_user_handler(
    request: UserCreateRequest = Body(..., description="User creation data"),
    user_service: UserService = Depends(get_user_service),
) -> UserCreateResponse:
    """
    Handle user creation request.
    For carpooling: Creates a new user (rider, driver, or admin).
    """
    user = await user_service.create_user(request.data)
    return UserCreateResponse(data=UserCreateResponseData.model_validate(user))


async def get_user_handler(
    user_id: str = Path(..., description="User ID to retrieve"),
    user_service: UserService = Depends(get_user_service),
) -> UserGetResponse:
    """
    Handle get user request.
    For carpooling: Retrieves user profile information.
    """
    user = await user_service.get_user_by_id(user_id)
    return UserGetResponse(data=UserGetResponseData.model_validate(user))


# Remove
async def get_users_handler(
    user_service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """
    Handle get users list request.
    For carpooling: Retrieves all registered users.
    """
    users = await user_service.get_all_users()
    return UserListResponse(
        data=[UserListResponseData.model_validate(user) for user in users]
    )
