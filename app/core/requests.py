from pydantic import BaseModel, Field, PositiveInt


class PaginationParams(BaseModel):
    """
    Pagination query parameters.
    """

    page: PositiveInt = Field(default=1, description="Page number")
    limit: PositiveInt = Field(default=10, le=100, description="Items per page")
