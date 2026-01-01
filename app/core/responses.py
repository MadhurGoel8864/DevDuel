# from typing import Generic, List, Optional, TypeVar, Union

# from pydantic import BaseModel, Field, NonNegativeInt

# T = TypeVar("T", bound=BaseModel)


# class APIResponse(BaseModel, Generic[T]):
#     """
#     Base API response schema.
#     """

#     success: bool = Field(default=True, description="Indicates if the request was successful")
#     data: Union[T, List[T], None] = Field(default=None, description="Response payload (single item or list of items)")


# class MessageData(BaseModel):
#     message: str = Field(..., description="Response message")


# class PaginatedResponse(APIResponse):
#     """
#     Paginated API response schema.
#     """

#     total: NonNegativeInt

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, NonNegativeInt

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """
    Standard API error response.
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(default=None)


class MetaResponse(BaseModel):
    """
    Optional metadata for API responses.
    """

    page: Optional[NonNegativeInt] = None
    limit: Optional[NonNegativeInt] = None
    total: Optional[NonNegativeInt] = None
    request_id: Optional[str] = None


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    """

    success: bool = Field(default=True)
    data: Optional[T] = None
    error: Optional[ErrorResponse] = None
    meta: Optional[MetaResponse] = None


class ListResponse(APIResponse[List[T]], Generic[T]):
    """
    Response schema for list endpoints.
    """

    pass


class PaginatedResponse(APIResponse[List[T]], Generic[T]):
    """
    Paginated API response schema.
    """

    meta: MetaResponse
