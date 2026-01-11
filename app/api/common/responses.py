"""
Common response schemas used across the application.

These schemas provide reusable response models for common patterns.
"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """
    Generic message response schema.

    Used for simple success/info messages across the application.
    """

    message: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True
