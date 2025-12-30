"""User API Schemas"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class BaseRequestSchema(BaseSchema):
    """Base schema for all request schemas"""

    pass


class BaseResponseSchema(BaseSchema, ISTDatetimeMixin):
    """Base schema for all response schemas with automatic IST timezone conversion"""

    pass


class UserCreateData(BaseSchema):
    """Data schema for creating a user"""

    email: EmailStr
    full_name: str


class UserCreateRequest(BaseRequestSchema):
    """Request schema for creating a user"""

    data: UserCreateData


class UserBaseData(BaseSchema):
    """Base user data schema with common fields"""

    id: str
    email: EmailStr
    full_name: str
    is_active: bool


class UserCreateResponseData(UserBaseData, ISTDatetimeMixin):
    """Response data schema for user creation"""

    created_at: datetime


class UserGetResponseData(UserBaseData, ISTDatetimeMixin):
    """Response data schema for getting a user"""

    created_at: datetime
    updated_at: datetime

class UserCreateResponse(BaseResponseSchema):
    """Response schema for user creation"""

    data: UserCreateResponseData


class UserGetResponse(BaseResponseSchema):
    """Response schema for getting a user"""

    data: UserGetResponseData
