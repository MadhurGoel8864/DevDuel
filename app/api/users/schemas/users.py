"""User API Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.responses import APIResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class BaseRequestSchema(BaseSchema):
    """
    Base schema for all request schemas.
    """

    pass


class UserCreateData(BaseSchema):
    """
    Data schema for creating a user.
    """

    email: EmailStr
    full_name: str
    password: str


class UserCreateRequest(BaseRequestSchema):
    """
    Request schema for creating a user.
    """

    data: UserCreateData


class UserBaseData(BaseSchema):
    """
    Base user data schema with common fields.
    """

    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool


class UserCreateResponseData(UserBaseData, ISTDatetimeMixin):
    """
    Response data for user creation.
    """

    created_at: datetime


class UserGetResponseData(UserBaseData, ISTDatetimeMixin):
    """
    Response data for getting a user.
    """

    created_at: datetime
    updated_at: datetime


# Remove
class UserListResponseData(UserBaseData, ISTDatetimeMixin):
    """
    Response data for listing users.
    """

    created_at: datetime
    updated_at: datetime


# Final response aliases
UserCreateResponse = APIResponse[UserCreateResponseData]
UserGetResponse = APIResponse[UserGetResponseData]
# Remove
UserListResponse = APIResponse[list[UserListResponseData]]
