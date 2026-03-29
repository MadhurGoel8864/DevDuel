# app/services/storage/__init__.py
"""
Cloud storage service module.

Provides a singleton GCS storage service for managing test case files.
"""

from app.services.storage.gcs import GCSStorageService

storage_service = GCSStorageService()

__all__ = ["storage_service"]
