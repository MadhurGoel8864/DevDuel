# app/services/judge0/client.py
"""
Async HTTP client for Judge0 CE API.

Handles submission creation, batch operations, polling, and language listing.
All text fields use base64 encoding for safe transport.
"""

import asyncio
import logging

import httpx

from app.core.config import settings
from app.services.judge0.constants import Judge0StatusId
from app.services.judge0.schemas import (
    Judge0Language,
    Judge0SubmissionRequest,
    Judge0SubmissionResult,
)

logger = logging.getLogger(__name__)


class Judge0Error(Exception):
    """Raised when a Judge0 API call fails."""

    pass


class Judge0TimeoutError(Judge0Error):
    """Raised when polling exceeds max attempts."""

    pass


class Judge0Client:
    """Async HTTP client for a self-hosted Judge0 CE instance."""

    def __init__(self):
        self._base_url = settings.JUDGE0_BASE_URL.rstrip("/")
        self._auth_token = settings.JUDGE0_AUTH_TOKEN
        self._max_batch_size = settings.JUDGE0_MAX_BATCH_SIZE
        self._poll_interval_ms = settings.JUDGE0_POLL_INTERVAL_MS
        self._poll_max_attempts = settings.JUDGE0_POLL_MAX_ATTEMPTS
        self._client: httpx.AsyncClient | None = None

    async def init(self) -> None:
        """Create the httpx async client. Call on app startup."""
        headers = {}
        if self._auth_token:
            headers["X-Auth-Token"] = self._auth_token

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=30.0,
        )
        logger.info(f"[judge0] Client initialized → {self._base_url}")

    async def close(self) -> None:
        """Close the httpx client. Call on app shutdown."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("[judge0] Client closed")

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise Judge0Error("Judge0 client not initialized. Call init() first.")
        return self._client

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """POST /authenticate — returns True if Judge0 is reachable and auth is valid."""
        try:
            resp = await self.client.post("/authenticate")
            logger.debug(f"[judge0] Health check response: {resp.status_code}")
            return resp.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"[judge0] Health check failed: {e}")
            return False

    # ── Single Submission ─────────────────────────────────────────────────────

    async def create_submission(
        self, submission: Judge0SubmissionRequest
    ) -> str:
        """Submit a single code execution. Returns the token."""
        logger.debug(
            f"[judge0] Creating submission: lang_id={submission.language_id}, "
            f"cpu_limit={submission.cpu_time_limit}s, mem_limit={submission.memory_limit}KB"
        )
        resp = await self.client.post(
            "/submissions",
            params={"base64_encoded": "true"},
            json=submission.model_dump(exclude_none=True),
        )
        if resp.status_code != 201:
            logger.error(
                f"[judge0] Submission creation failed: "
                f"status={resp.status_code}, body={resp.text}"
            )
            raise Judge0Error(
                f"Failed to create submission: {resp.status_code} {resp.text}"
            )
        token = resp.json()["token"]
        logger.info(f"[judge0] Submission created: token={token}")
        return token

    async def get_submission(
        self, token: str, fields: str = "*"
    ) -> Judge0SubmissionResult:
        """Fetch a single submission result."""
        logger.debug(f"[judge0] Fetching submission: token={token}")
        resp = await self.client.get(
            f"/submissions/{token}",
            params={"base64_encoded": "true", "fields": fields},
        )
        if resp.status_code != 200:
            logger.error(
                f"[judge0] Get submission failed: token={token}, "
                f"status={resp.status_code}, body={resp.text}"
            )
            raise Judge0Error(
                f"Failed to get submission {token}: {resp.status_code} {resp.text}"
            )
        result = Judge0SubmissionResult(**resp.json())
        logger.debug(
            f"[judge0] Submission {token}: status={result.status.id} "
            f"({result.status.description}), time={result.time}s, memory={result.memory}KB"
        )
        return result

    # ── Batch Submissions ─────────────────────────────────────────────────────

    async def create_batch_submissions(
        self, submissions: list[Judge0SubmissionRequest]
    ) -> list[str]:
        """Submit a batch of up to max_batch_size executions. Returns list of tokens.

        If submissions exceed max_batch_size, splits into multiple requests.
        """
        logger.info(
            f"[judge0] Batch create: {len(submissions)} submissions, "
            f"chunk_size={self._max_batch_size}"
        )
        all_tokens: list[str] = []

        for i in range(0, len(submissions), self._max_batch_size):
            chunk = submissions[i : i + self._max_batch_size]
            chunk_num = i // self._max_batch_size + 1
            logger.debug(f"[judge0] Sending batch chunk {chunk_num}: {len(chunk)} submissions")

            payload = {
                "submissions": [s.model_dump(exclude_none=True) for s in chunk]
            }
            resp = await self.client.post(
                "/submissions/batch",
                params={"base64_encoded": "true"},
                json=payload,
            )
            if resp.status_code != 201:
                logger.error(
                    f"[judge0] Batch chunk {chunk_num} failed: "
                    f"status={resp.status_code}, body={resp.text}"
                )
                raise Judge0Error(
                    f"Batch submission failed: {resp.status_code} {resp.text}"
                )

            tokens = [item["token"] for item in resp.json()]
            all_tokens.extend(tokens)
            logger.debug(f"[judge0] Batch chunk {chunk_num} OK: tokens={tokens}")

        logger.info(f"[judge0] Batch create complete: {len(all_tokens)} tokens")
        return all_tokens

    async def get_batch_submissions(
        self, tokens: list[str], fields: str = "*"
    ) -> list[Judge0SubmissionResult]:
        """Fetch results for multiple tokens in one request.

        Splits into chunks of max_batch_size if needed.
        """
        logger.debug(f"[judge0] Batch get: {len(tokens)} tokens")
        all_results: list[Judge0SubmissionResult] = []

        for i in range(0, len(tokens), self._max_batch_size):
            chunk = tokens[i : i + self._max_batch_size]
            token_str = ",".join(chunk)
            resp = await self.client.get(
                "/submissions/batch",
                params={
                    "tokens": token_str,
                    "base64_encoded": "true",
                    "fields": fields,
                },
            )
            if resp.status_code != 200:
                logger.error(
                    f"[judge0] Batch get failed: status={resp.status_code}, body={resp.text}"
                )
                raise Judge0Error(
                    f"Batch get failed: {resp.status_code} {resp.text}"
                )

            results = [
                Judge0SubmissionResult(**item)
                for item in resp.json()["submissions"]
            ]
            statuses = {r.status.description for r in results}
            logger.debug(
                f"[judge0] Batch get results: {len(results)} submissions, "
                f"statuses={statuses}"
            )
            all_results.extend(results)

        return all_results

    # ── Polling ───────────────────────────────────────────────────────────────

    async def poll_batch_until_done(
        self, tokens: list[str]
    ) -> list[Judge0SubmissionResult]:
        """Poll batch submissions until all have status.id >= 3 (finished).

        Uses configured poll interval and max attempts.

        Raises:
            Judge0TimeoutError: If max attempts exceeded with submissions still processing.
        """
        interval_s = self._poll_interval_ms / 1000.0
        logger.info(
            f"[judge0] Polling started: {len(tokens)} tokens, "
            f"interval={interval_s}s, max_attempts={self._poll_max_attempts}"
        )

        for attempt in range(1, self._poll_max_attempts + 1):
            results = await self.get_batch_submissions(tokens)

            still_processing = [
                r for r in results
                if r.status.id <= Judge0StatusId.PROCESSING
            ]

            if not still_processing:
                verdicts = [r.status.description for r in results]
                logger.info(
                    f"[judge0] Polling complete after {attempt} poll(s): "
                    f"verdicts={verdicts}"
                )
                return results

            logger.debug(
                f"[judge0] Poll {attempt}/{self._poll_max_attempts}: "
                f"{len(still_processing)}/{len(tokens)} still processing, "
                f"waiting {interval_s}s"
            )
            await asyncio.sleep(interval_s)

        logger.error(
            f"[judge0] Polling timed out after {self._poll_max_attempts} attempts: "
            f"{len(still_processing)}/{len(tokens)} still processing"
        )
        raise Judge0TimeoutError(
            f"Polling timed out after {self._poll_max_attempts} attempts. "
            f"{len(still_processing)} submissions still processing."
        )

    async def poll_batch_fail_fast(
        self, tokens: list[str]
    ) -> list[Judge0SubmissionResult]:
        """Poll batch submissions, returning early on the first failure.

        Returns as soon as any token has a non-ACCEPTED terminal status, or once
        every token reaches ACCEPTED. Tokens still IN_QUEUE/PROCESSING when a
        failure is found are returned as-is (status.id <= 2) — callers must skip them.

        Raises:
            Judge0TimeoutError: If max attempts exceeded with submissions still processing.
        """
        interval_s = self._poll_interval_ms / 1000.0
        logger.info(
            f"[judge0] Fail-fast polling: {len(tokens)} tokens, "
            f"interval={interval_s}s, max_attempts={self._poll_max_attempts}"
        )

        still_processing: list[Judge0SubmissionResult] = []
        for attempt in range(1, self._poll_max_attempts + 1):
            results = await self.get_batch_submissions(tokens)

            still_processing = [
                r for r in results if r.status.id <= Judge0StatusId.PROCESSING
            ]

            has_failure = any(
                r.status.id > Judge0StatusId.PROCESSING
                and r.status.id != Judge0StatusId.ACCEPTED
                for r in results
            )
            if has_failure:
                logger.info(
                    f"[judge0] Fail-fast exit after {attempt} poll(s): "
                    f"{len(still_processing)}/{len(tokens)} still pending (not awaited)"
                )
                return results

            if not still_processing:
                verdicts = [r.status.description for r in results]
                logger.info(
                    f"[judge0] Fail-fast polling complete after {attempt} poll(s): "
                    f"verdicts={verdicts}"
                )
                return results

            logger.debug(
                f"[judge0] Poll {attempt}/{self._poll_max_attempts}: "
                f"{len(still_processing)}/{len(tokens)} still processing, "
                f"waiting {interval_s}s"
            )
            await asyncio.sleep(interval_s)

        logger.error(
            f"[judge0] Fail-fast polling timed out after {self._poll_max_attempts} attempts: "
            f"{len(still_processing)}/{len(tokens)} still processing"
        )
        raise Judge0TimeoutError(
            f"Polling timed out after {self._poll_max_attempts} attempts. "
            f"{len(still_processing)} submissions still processing."
        )

    # ── Languages ─────────────────────────────────────────────────────────────

    async def get_languages(self) -> list[Judge0Language]:
        """Fetch all active languages from Judge0."""
        resp = await self.client.get("/languages")
        if resp.status_code != 200:
            raise Judge0Error(
                f"Failed to get languages: {resp.status_code} {resp.text}"
            )
        return [Judge0Language(**lang) for lang in resp.json()]
