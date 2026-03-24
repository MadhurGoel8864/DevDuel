from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    page: int
    limit: int

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


async def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number (min: 1)"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Items per page (min: 1, max: 100)"
    ),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit)
