"""User Handler Layer"""

from fastapi import Body, Depends, HTTPException, Path

from app.api.users.schemas.users import (
    UserCreateRequest,
    UserCreateResponse,
    UserCreateResponseData,
    UserGetResponse,
    UserGetResponseData,
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
    try:
        user = await user_service.create_user(request.data)
        return UserCreateResponse(data=UserCreateResponseData.model_validate(user))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error in production
        raise HTTPException(status_code=500, detail=f"Internal server error, {e}")


async def get_user_handler(
    user_id: str = Path(..., description="User ID to retrieve"),
    user_service: UserService = Depends(get_user_service),
) -> UserGetResponse:
    """
    Handle get user request.
    For carpooling: Retrieves user profile information.
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserGetResponse(data=UserGetResponseData.model_validate(user))
