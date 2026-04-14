"""Redis Pub/Sub fanout for bidding websocket events."""

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.api.bidding.connection_manager import manager
from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_CHANNEL_TEMPLATE = "contest:{contest_id}:bidding"
_CHANNEL_PATTERN = "contest:*:bidding"
_INSTANCE_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def build_channel(contest_id: str) -> str:
    return _CHANNEL_TEMPLATE.format(contest_id=contest_id)


def _extract_contest_id(channel: str) -> str | None:
    if not channel.startswith("contest:"):
        return None
    parts = channel.split(":")
    if len(parts) != 3 or parts[2] != "bidding":
        return None
    return parts[1]


def _build_envelope(contest_id: str, payload: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": payload.get("type", "UNKNOWN"),
        "contest_id": contest_id,
        "payload": payload,
        "server_time": _now_iso(),
        "producer_instance": _INSTANCE_ID,
    }


async def publish_bidding_event(contest_id: str, payload: dict) -> None:
    redis = await get_redis()
    envelope = _build_envelope(contest_id=contest_id, payload=payload)
    await redis.publish(build_channel(contest_id), json.dumps(envelope))


async def fanout_bidding_event(contest_id: str, payload: dict) -> None:
    """
    Fanout bidding event to websocket clients.

    When Redis Pub/Sub is enabled, this publishes to Redis and lets the
    subscriber broadcast locally. Otherwise, it falls back to local broadcast.
    """
    if settings.BIDDING_REDIS_PUBSUB_ENABLED:
        await publish_bidding_event(contest_id=contest_id, payload=payload)
        return
    await manager.broadcast_local(contest_id=contest_id, message=payload)


class BiddingEventSubscriber:
    """Consumes Redis pub/sub bidding events and broadcasts to local sockets."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._pubsub = None
        self._stopping = False

    async def start(
        self, on_event: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(
            self._run(on_event),
            name="bidding-event-subscriber",
        )
        logger.info("[bidding-pubsub] subscriber started")

    async def stop(self) -> None:
        self._stopping = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await self._close_pubsub()
        logger.info("[bidding-pubsub] subscriber stopped")

    async def _run(self, on_event: Callable[[str, dict], Awaitable[None]]) -> None:
        backoff_seconds = 1
        while not self._stopping:
            try:
                await self._ensure_subscription()
                backoff_seconds = 1
                while not self._stopping:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    if message is None:
                        await asyncio.sleep(0.05)
                        continue
                    await self._handle_message(message, on_event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    f"[bidding-pubsub] subscriber loop error: {exc!r}",
                    exc_info=True,
                )
                await self._close_pubsub()
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 10)

    async def _ensure_subscription(self) -> None:
        if self._pubsub is not None:
            return
        redis = await get_redis()
        self._pubsub = redis.pubsub(ignore_subscribe_messages=True)
        await self._pubsub.psubscribe(_CHANNEL_PATTERN)
        logger.info(
            f"[bidding-pubsub] subscribed to pattern={_CHANNEL_PATTERN}"
        )

    async def _close_pubsub(self) -> None:
        if self._pubsub is None:
            return
        try:
            await self._pubsub.close()
        except Exception:
            logger.warning(
                "[bidding-pubsub] failed closing pubsub cleanly",
                exc_info=True,
            )
        finally:
            self._pubsub = None

    async def _handle_message(
        self,
        message: dict,
        on_event: Callable[[str, dict], Awaitable[None]],
    ) -> None:
        raw_channel = message.get("channel")
        if not isinstance(raw_channel, str):
            return
        raw_data = message.get("data")
        if not isinstance(raw_data, str):
            return

        try:
            envelope = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.warning(
                f"[bidding-pubsub] dropped malformed json on channel={raw_channel}"
            )
            return
        if not isinstance(envelope, dict):
            logger.warning(
                f"[bidding-pubsub] dropped non-object payload on channel={raw_channel}"
            )
            return

        contest_id = envelope.get("contest_id")
        payload = envelope.get("payload")
        if not isinstance(contest_id, str):
            contest_id = _extract_contest_id(raw_channel)
        if not isinstance(contest_id, str) or not isinstance(payload, dict):
            logger.warning(
                f"[bidding-pubsub] dropped invalid envelope on channel={raw_channel}"
            )
            return

        await on_event(contest_id, payload)


bidding_event_subscriber = BiddingEventSubscriber()
