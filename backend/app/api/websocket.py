"""WebSocket support for real-time scraping job progress updates.

Uses Redis Pub/Sub as a backplane so that progress messages are broadcast
reliably across all Uvicorn/Gunicorn worker processes.

Clients connect via WebSocket and receive JSON messages like::

    {"type": "job_progress", "job_id": "...", "status": "running", "leads_found": 5}
    {"type": "job_completed", "job_id": "...", "leads_found": 42}
    {"type": "job_failed", "job_id": "...", "error": "..."}
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user_ws

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


# ---------------------------------------------------------------------------
# Connection manager — tracks active WebSocket connections
# ---------------------------------------------------------------------------
class ConnectionManager:
    """Manages WebSocket connections grouped by user ID.

    In a multi-worker deployment, each worker has its own ConnectionManager
    instance.  Messages are broadcast via Redis Pub/Sub so all workers
    receive them and can forward to their connected clients.
    """

    def __init__(self) -> None:
        # user_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        self._redis_sub = None
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        logger.info("WebSocket connected: user=%s, total=%d", user_id, self._total_connections())

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    def _total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Send a message to all WebSocket connections for a user."""
        connections = self._connections.get(user_id, set())
        if not connections:
            return

        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_via_redis(self, user_id: str, message: dict) -> None:
        """Publish a message to Redis Pub/Sub for cross-worker delivery.

        Each worker's subscriber picks up the message and calls
        ``send_to_user`` to deliver it to locally connected clients.
        """
        try:
            import redis.asyncio as aioredis
            from app.config import settings

            r = aioredis.from_url(settings.REDIS_URL)
            channel = f"ws:user:{user_id}"
            await r.publish(channel, json.dumps(message))
            await r.aclose()
        except Exception:
            logger.exception("Failed to publish to Redis Pub/Sub")

    async def start_redis_subscriber(self) -> None:
        """Subscribe to Redis Pub/Sub and forward messages to local clients.

        Should be called once when the application starts.
        """
        try:
            import redis.asyncio as aioredis
            from app.config import settings

            self._redis_sub = aioredis.from_url(settings.REDIS_URL)
            pubsub = self._redis_sub.pubsub()
            await pubsub.psubscribe("ws:user:*")

            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue

                try:
                    data = json.loads(message["data"])
                    # Extract user_id from channel: "ws:user:{user_id}"
                    channel_name = message["channel"]
                    user_id = channel_name.split(":")[-1] if ":" in channel_name else ""
                    if user_id:
                        await self.send_to_user(user_id, data)
                except Exception:
                    logger.exception("Error processing Redis Pub/Sub message")

        except Exception:
            logger.exception("Redis Pub/Sub subscriber failed")

    async def stop_redis_subscriber(self) -> None:
        """Stop the Redis subscriber."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            self._pubsub_task = None
        if self._redis_sub:
            await self._redis_sub.aclose()
            self._redis_sub = None


# Global connection manager instance
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """WebSocket endpoint for real-time job progress updates.

    Authenticate via query parameter: ``ws://host/ws?token=<jwt>``

    Messages received (client -> server):
        {"action": "subscribe_jobs"} — subscribe to job updates (default)

    Messages sent (server -> client):
        {"type": "job_progress", "job_id": "...", ...}
        {"type": "job_completed", "job_id": "...", ...}
        {"type": "job_failed", "job_id": "...", ...}
    """
    from app.api.deps import get_current_user

    # Authenticate via JWT token in query param
    try:
        from app.api.deps import oauth2_scheme
        user = await get_current_user(token=token)
        user_id = str(user.id)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await manager.connect(user_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            # Client messages are acknowledged but not acted upon yet
            # Future: allow subscribe/unsubscribe to specific jobs
            logger.debug("WebSocket message from user %s: %s", user_id, raw[:100])
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: user=%s", user_id)
