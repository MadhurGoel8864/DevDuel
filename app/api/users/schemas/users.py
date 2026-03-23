"""User API Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.responses import APIResponse
from app.core.security.password import PasswordStr
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
    password: PasswordStr


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
    username: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    is_organizer: bool = False
    profile_img_url: str | None = None


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
    last_login_at: datetime | None = None
    email_verified_at: datetime | None = None


# Remove
class UserListResponseData(UserBaseData, ISTDatetimeMixin):
    """
    Response data for listing users.
    """

    created_at: datetime
    updated_at: datetime


class UserUpdateData(BaseSchema):
    """
    Data schema for updating a user's profile.
    Both fields are optional; only provided fields are updated.
    """

    full_name: str | None = None
    username: str | None = None


class UserUpdateRequest(BaseRequestSchema):
    """
    Request schema for updating a user's profile.
    """

    data: UserUpdateData


class UserUpdateResponseData(UserBaseData, ISTDatetimeMixin):
    """
    Response data after updating a user's profile.
    """

    created_at: datetime
    updated_at: datetime


# Final response aliases
UserCreateResponse = APIResponse[UserCreateResponseData]
UserGetResponse = APIResponse[UserGetResponseData]
UserUpdateResponse = APIResponse[UserUpdateResponseData]
# Remove
UserListResponse = APIResponse[list[UserListResponseData]]
