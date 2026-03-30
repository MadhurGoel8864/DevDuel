# app/services/storage/gcs.py
"""
Google Cloud Storage service for managing test case files.

Test cases are stored as JSON files in GCS with the structure:
    gs://<bucket>/problems/<problem_slug>/testcases.json

Each JSON file contains a list of test case objects:
    [
        {"input": "...", "expected_output": "...", "is_sample": true},
        {"input": "...", "expected_output": "...", "is_sample": false}
    ]
"""

import json
import logging
from typing import Any

from google.cloud import storage
from google.oauth2 import service_account

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when a cloud storage operation fails."""

    pass


class GCSStorageService:
    """Google Cloud Storage service for test case file management."""

    def __init__(self):
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None

    def _get_client(self) -> storage.Client:
        """Lazy-init the GCS client on first use.

        Supports two auth modes:
        - GCS_SERVICE_ACCOUNT_KEY_JSON: raw JSON string (for server/CI deployments)
        - GCS_SERVICE_ACCOUNT_KEY_PATH: path to a JSON key file (for local dev)
        """
        if self._client is None:
            key_json = settings.GCS_SERVICE_ACCOUNT_KEY_JSON
            key_path = settings.GCS_SERVICE_ACCOUNT_KEY_PATH
            project_id = settings.GCS_PROJECT_ID

            if not key_json and not key_path:
                raise StorageError(
                    "GCS credentials not configured. Set either "
                    "GCS_SERVICE_ACCOUNT_KEY_JSON or GCS_SERVICE_ACCOUNT_KEY_PATH."
                )

            try:
                if key_json:
                    info = json.loads(key_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        info
                    )
                    logger.info("GCS client initialized from JSON env var")
                else:
                    credentials = service_account.Credentials.from_service_account_file(
                        key_path
                    )
                    logger.info("GCS client initialized from key file")

                self._client = storage.Client(
                    project=project_id, credentials=credentials
                )
            except json.JSONDecodeError as e:
                logger.error(f"Invalid GCS_SERVICE_ACCOUNT_KEY_JSON: {e}")
                raise StorageError(f"Invalid GCS service account JSON: {e}") from e
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise StorageError(f"Failed to initialize GCS client: {e}") from e

        return self._client

    def _get_bucket(self) -> storage.Bucket:
        """Get the configured GCS bucket."""
        if self._bucket is None:
            client = self._get_client()
            bucket_name = settings.GCS_BUCKET_NAME
            self._bucket = client.bucket(bucket_name)
        return self._bucket

    def _blob_path(self, problem_slug: str) -> str:
        """Build the GCS blob path for a problem's test cases."""
        return f"problems/{problem_slug}/testcases.json"

    def upload_test_cases(
        self, problem_slug: str, test_cases: list[dict[str, Any]]
    ) -> str:
        """Upload test cases JSON to GCS.

        Args:
            problem_slug: The problem's slug (used as folder name).
            test_cases: List of test case dicts with keys:
                input, expected_output, is_sample.

        Returns:
            The public GCS URL of the uploaded file.

        Raises:
            StorageError: If the upload fails.
        """
        bucket = self._get_bucket()
        blob_path = self._blob_path(problem_slug)
        blob = bucket.blob(blob_path)

        try:
            json_data = json.dumps(test_cases, ensure_ascii=False, indent=2)
            blob.upload_from_string(json_data, content_type="application/json")

            url = f"gs://{settings.GCS_BUCKET_NAME}/{blob_path}"
            logger.info(f"Uploaded test cases for '{problem_slug}' → {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload test cases for '{problem_slug}': {e}")
            raise StorageError(
                f"Failed to upload test cases for '{problem_slug}': {e}"
            ) from e

    def download_test_cases(self, problem_slug: str) -> list[dict[str, Any]]:
        """Download and parse test cases JSON from GCS.

        Args:
            problem_slug: The problem's slug.

        Returns:
            List of test case dicts.

        Raises:
            StorageError: If the download or parsing fails.
        """
        bucket = self._get_bucket()
        blob_path = self._blob_path(problem_slug)
        blob = bucket.blob(blob_path)

        try:
            raw = blob.download_as_text(encoding="utf-8")
            test_cases = json.loads(raw)
            logger.info(
                f"Downloaded {len(test_cases)} test cases for '{problem_slug}'"
            )
            return test_cases

        except Exception as e:
            logger.error(f"Failed to download test cases for '{problem_slug}': {e}")
            raise StorageError(
                f"Failed to download test cases for '{problem_slug}': {e}"
            ) from e

    def download_test_cases_from_url(self, gcs_url: str) -> list[dict[str, Any]]:
        """Download and parse test cases from a full GCS URL.

        Args:
            gcs_url: Full GCS URL (gs://bucket/path/to/testcases.json).

        Returns:
            List of test case dicts.

        Raises:
            StorageError: If the URL format is invalid or download fails.
        """
        if not gcs_url.startswith("gs://"):
            raise StorageError(f"Invalid GCS URL format: {gcs_url}")

        # Parse gs://bucket-name/blob/path
        without_prefix = gcs_url[5:]  # Remove "gs://"
        slash_idx = without_prefix.index("/")
        bucket_name = without_prefix[:slash_idx]
        blob_path = without_prefix[slash_idx + 1 :]

        try:
            client = self._get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            raw = blob.download_as_text(encoding="utf-8")
            test_cases = json.loads(raw)
            logger.info(f"Downloaded {len(test_cases)} test cases from {gcs_url}")
            return test_cases

        except Exception as e:
            logger.error(f"Failed to download test cases from '{gcs_url}': {e}")
            raise StorageError(
                f"Failed to download test cases from '{gcs_url}': {e}"
            ) from e

    def delete_test_cases(self, problem_slug: str) -> None:
        """Delete test cases file from GCS.

        Args:
            problem_slug: The problem's slug.

        Raises:
            StorageError: If the deletion fails.
        """
        bucket = self._get_bucket()
        blob_path = self._blob_path(problem_slug)
        blob = bucket.blob(blob_path)

        try:
            blob.delete()
            logger.info(f"Deleted test cases for '{problem_slug}'")
        except Exception as e:
            logger.error(f"Failed to delete test cases for '{problem_slug}': {e}")
            raise StorageError(
                f"Failed to delete test cases for '{problem_slug}': {e}"
            ) from e

    def test_cases_exist(self, problem_slug: str) -> bool:
        """Check if test cases file exists in GCS."""
        bucket = self._get_bucket()
        blob_path = self._blob_path(problem_slug)
        blob = bucket.blob(blob_path)
        return blob.exists()
