"""
Shared WebSocket ConnectionManager singleton.

Kept in its own module so both websocket.py and services.py can import it
without creating circular dependencies.
"""

import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by contest_id.

    Each contest has its own broadcast room — clients only receive messages
    relevant to the contest they are connected to.
    """

    def __init__(self):
        # contest_id → list of active WebSocket connections
        self._rooms: dict[str, list[WebSocket]] = defaultdict(list)

    def room_size(self, contest_id: str) -> int:
        """Return the number of active WebSockets in a contest room."""
        return len(self._rooms.get(contest_id, []))

    async def connect(self, websocket: WebSocket, contest_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._rooms[contest_id].append(websocket)
        logger.info(
            f"WS connected to contest {contest_id}. "
            f"Total in room: {len(self._rooms[contest_id])}"
        )

    def disconnect(self, websocket: WebSocket, contest_id: str) -> None:
        """Remove a disconnected WebSocket from the room."""
        if websocket in self._rooms[contest_id]:
            self._rooms[contest_id].remove(websocket)
        logger.info(
            f"WS disconnected from contest {contest_id}. "
            f"Remaining: {len(self._rooms[contest_id])}"
        )

    async def broadcast(self, contest_id: str, message: dict) -> None:
        """Send a JSON message to every client in a contest room."""
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self._rooms[contest_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self._rooms[contest_id]:
                self._rooms[contest_id].remove(ws)


# Module-level singleton — import this everywhere instead of instantiating locally
manager = ConnectionManager()
