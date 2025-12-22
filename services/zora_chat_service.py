# --- services/zora_chat_service.py ---
"""
Zora Livestream Chat Service for Pokemon LLM Agent.
Connects to Zora's GraphQL WebSocket API to read chat messages from a livestream.

Protocol: graphql-transport-ws
Endpoint: wss://api.zora.co/universal/graphql
HTTP Endpoint: https://api.zora.co/universal/graphql (for resolving stream ID)
"""

import asyncio
import json
import logging
import time
import random
import os
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any
from collections import deque

log = logging.getLogger("zora_chat")

# Check if websockets/httpx are available
try:
    import websockets
    from websockets.client import WebSocketClientProtocol

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    log.warning("websockets not installed. Zora chat integration disabled.")

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    log.warning("httpx not installed. Zora stream ID lookup disabled.")


# Configuration
ZORA_WS_URL = "wss://api.zora.co/universal/graphql"
ZORA_HTTP_URL = "https://api.zora.co/universal/graphql"

# Test mode configuration
CHAT_TEST_MODE = os.getenv("CHAT_TEST_MODE", "false").lower() == "true"

TEST_USERNAMES = [
    "ZorbLover",
    "BaseBuilder",
    "MintMaster",
    "OnchainGamer",
    "WagmiWarrior",
    "ZoraExplorer",
    "PixelPusher",
    "EthMaxi",
    "Layer2Legend",
    "CryptoPunk",
]

TEST_MESSAGES = [
    "This stream is onchain!",
    "Minting this moment",
    "LFG Zora",
    "Is this running on Base?",
    "Nice catch!",
    "We need more balls",
    "Check the floor price",
    "gm",
    "gn",
    "What generation is this?",
    "Can I mint the gym battle?",
    "based",
    "pure signal",
    "minted",
]


@dataclass
class ZoraChatMessage:
    """Represents a chat message from Zora."""

    id: str
    username: str  # handle
    message: str  # comment
    avatar_url: str
    timestamp: float
    user_address: str = ""  # For token gating (if available in future)
    responded: bool = False
    is_test: bool = False


class ZoraChatService:
    """
    Manages Zora livestream chat connection.

    Features:
    - Resolves Zora username to Stream ID via HTTP
    - Connects via WebSocket (graphql-transport-ws)
    - Subscribes to onLiveStreamComment
    - Handles keep-alives and reconnection
    """

    def __init__(
        self,
        username: Optional[str] = None,
        on_message_callback: Optional[Callable] = None,
        message_history_limit: int = 100,
    ):
        """
        Initialize the Zora chat service.

        Args:
            username: The Zora username (handle) to spectate
            on_message_callback: Optional callback for new messages
            message_history_limit: Max messages to keep in memory
        """
        self.username = username or os.getenv("ZORA_USERNAME", "")
        self.on_message_callback = on_message_callback
        self.message_history_limit = message_history_limit

        # Connection state
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._stream_id: Optional[str] = None

        # Message storage
        self._message_queue: deque[ZoraChatMessage] = deque(
            maxlen=message_history_limit
        )
        self._last_commentary_timestamp: float = 0

        # Tasks
        self._ping_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        # Test mode
        self._test_mode = CHAT_TEST_MODE

        self._is_configured = bool(self.username)

        if self._test_mode:
            log.info("🧪 Zora Chat TEST MODE enabled")
        elif not self._is_configured:
            log.warning("Zora chat not configured. Set ZORA_USERNAME in .env")

    @property
    def is_available(self) -> bool:
        """Check if service is available."""
        if self._test_mode:
            return True
        return WEBSOCKETS_AVAILABLE and HTTPX_AVAILABLE and self._is_configured

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self) -> bool:
        """Start the service."""
        if not self.is_available:
            log.warning(
                "Cannot start Zora chat - dependencies missing or config invalid"
            )
            return False

        if self._running:
            return True

        self._running = True

        if not self._test_mode:
            # Resolve Stream ID first
            if not self._stream_id:
                self._stream_id = await self._fetch_stream_id(self.username)
                if not self._stream_id:
                    log.error(f"Could not find livestream for user: {self.username}")
                    # We don't stop here, we might retry later or if network comes up
                    # But for now let's just log error.

            asyncio.create_task(self._connect_loop())

        log.info(f"Zora chat service started for user: {self.username}")
        return True

    async def stop(self):
        """Stop the service."""
        self._running = False
        self._connected = False

        if self._ping_task:
            self._ping_task.cancel()

        if self._ws:
            await self._ws.close()

        log.info("Zora chat service stopped")

    async def _fetch_stream_id(self, username: str) -> Optional[str]:
        """Fetch stream ID from username using Zora GraphQL API."""
        if not HTTPX_AVAILABLE:
            log.warning("Cannot fetch stream ID: httpx not installed")
            return None

        query = """
        query getStreamIdFromUsername($username: String!) {
          profile(identifier: $username) {
            ... on GraphQLAccountProfile {
              liveStream {
                streamId
              }
            }
          }
        }
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ZORA_HTTP_URL,
                    json={"query": query, "variables": {"username": username}},
                    timeout=10.0,
                )

                if response.status_code != 200:
                    log.error(f"Zora API error: {response.status_code} {response.text}")
                    return None

                data = response.json()
                stream_id = (
                    data.get("data", {})
                    .get("profile", {})
                    .get("liveStream", {})
                    .get("streamId")
                )

                if stream_id:
                    log.info(f"Found Zora stream ID for {username}: {stream_id}")
                    return stream_id
                else:
                    log.warning(f"No active stream found for Zora user: {username}")
                    return None

        except Exception as e:
            log.error(f"Failed to fetch Zora stream ID: {e}")
            return None

    async def _connect_loop(self):
        """Main connection loop."""
        while self._running:
            try:
                # If we don't have a stream ID yet, try to get it
                if not self._stream_id:
                    self._stream_id = await self._fetch_stream_id(self.username)
                    if not self._stream_id:
                        # Wait a bit before retrying lookup
                        await asyncio.sleep(60)
                        continue

                await self._connect()

            except Exception as e:
                log.error(f"Zora connection error: {e}")
                self._connected = False

                # Exponential backoff
                retry_delay = min(2**self._reconnect_attempts, 60)
                self._reconnect_attempts += 1

                log.info(f"Reconnecting to Zora in {retry_delay}s...")
                await asyncio.sleep(retry_delay)

    async def _connect(self):
        """Establish WebSocket connection."""
        if not WEBSOCKETS_AVAILABLE:
            log.error("Cannot connect: websockets not installed")
            return

        log.info(f"Connecting to Zora Chat WS (Stream ID: {self._stream_id})...")

        async with websockets.connect(
            ZORA_WS_URL, subprotocols=["graphql-transport-ws"]
        ) as ws:
            self._ws = ws
            self._reconnect_attempts = 0

            # 1. Connection Init
            await ws.send(json.dumps({"type": "connection_init"}))

            # 2. Wait for Ack and start loop
            async for message in ws:
                await self._handle_message(message)

    async def _handle_message(self, raw_msg: str):
        """Handle incoming WebSocket message."""
        try:
            msg = json.loads(raw_msg)
            msg_type = msg.get("type")

            if msg_type == "connection_ack":
                self._connected = True
                log.info("✅ Connected to Zora Chat!")

                # Start Ping Task (Client-side keep-alive)
                if self._ping_task:
                    self._ping_task.cancel()
                self._ping_task = asyncio.create_task(self._ping_loop())

                # Subscribe to chat
                await self._subscribe()

            elif msg_type == "next":
                # Data payload
                payload = msg.get("payload", {})
                await self._process_data_payload(payload)

            elif msg_type == "error":
                log.error(f"Zora WS Error: {msg.get('payload')}")

            elif msg_type == "complete":
                log.info("Zora subscription complete (server closed stream?)")
                # Server might close idle streams. We should probably reconnect/resubscribe.
                raise Exception("Subscription completed by server")

            elif msg_type == "ping":
                # Server sent ping? Protocol usually says client sends ping, but handle just in case
                await self._send({"type": "pong"})

            elif msg_type == "pong":
                # Response to our ping
                pass

        except json.JSONDecodeError:
            log.warning(f"Invalid JSON from Zora: {raw_msg}")
        except Exception as e:
            log.error(f"Error handling Zora message: {e}")
            raise  # Trigger reconnect

    async def _subscribe(self):
        """Send subscription message."""
        query = """
          subscription OnLiveStreamComment($liveStreamId: String!) {
            onLiveStreamComment(liveStreamId: $liveStreamId) {
              add {
                node {
                  id
                  profile {
                    handle
                    address
                    avatar {
                      small
                    }
                  }
                  comment
                  commentedAt
                }
              }
            }
          }
        """

        sub_msg = {
            "id": "1",
            "type": "subscribe",
            "payload": {"query": query, "variables": {"liveStreamId": self._stream_id}},
        }
        await self._send(sub_msg)
        log.info("Subscribed to Zora comments")

    async def _process_data_payload(self, payload: Dict):
        """Process 'next' message payload."""
        data = payload.get("data", {})
        event = data.get("onLiveStreamComment", {})
        added_items = event.get("add", [])

        if not added_items:
            return

        for item in added_items:
            node = item.get("node", {})
            profile = node.get("profile", {})

            # Extract fields
            msg_id = node.get("id", f"zora_{time.time()}")
            handle = profile.get("handle", "Unknown")
            address = profile.get("address", "")
            avatar = profile.get("avatar", {}).get("small", "")
            comment = node.get("comment", "")

            # Create object
            chat_msg = ZoraChatMessage(
                id=msg_id,
                username=handle,
                message=comment,
                avatar_url=avatar,
                timestamp=time.time(),
                user_address=address,
            )

            # Store
            self._message_queue.append(chat_msg)
            log.info(f"🟣 Zora [{handle}]: {comment}")

            # Callback
            if self.on_message_callback:
                try:
                    self.on_message_callback(chat_msg)
                except Exception as e:
                    log.error(f"Error in Zora message callback: {e}")

    async def _ping_loop(self):
        """Send pings every 10 seconds."""
        while self._running and self._connected:
            try:
                await asyncio.sleep(10)
                await self._send({"type": "ping"})
            except Exception:
                break

    async def _send(self, payload: Dict):
        """Send JSON payload."""
        if self._ws:
            await self._ws.send(json.dumps(payload))

    def mark_commentary_timestamp(self):
        """Mark when last commentary was generated."""
        self._last_commentary_timestamp = time.time()

    def get_messages_for_cycle(self) -> List[dict]:
        """Get messages for LLM processing."""
        cutoff = self._last_commentary_timestamp

        # Filter messages
        messages = [
            msg
            for msg in self._message_queue
            if not msg.responded and msg.timestamp > cutoff
        ]

        # Sort oldest first
        messages.sort(key=lambda m: m.timestamp)

        return [
            {
                "username": msg.username,
                "display_name": msg.username,
                "message": msg.message,
                "timestamp": msg.timestamp,
                "user_address": msg.user_address,
                "source": "zora",
                "_original": msg,
            }
            for msg in messages
        ]

    def get_messages_for_cycle_or_test(self) -> List[dict]:
        """Get messages (real or test)."""
        if self._test_mode:
            return self.generate_test_messages()
        return self.get_messages_for_cycle()

    def generate_test_messages(self, count: int = 2) -> List[dict]:
        """Generate fake messages."""
        msgs = []
        base_time = time.time()

        # Only generate occasionally
        if random.random() > 0.3:
            return []

        for i in range(count):
            username = random.choice(TEST_USERNAMES)
            message = random.choice(TEST_MESSAGES)

            msgs.append(
                {
                    "username": username,
                    "display_name": username,
                    "message": message,
                    "timestamp": base_time - (count - i) * 1.0,
                    "user_address": f"0xTEST{username}",
                    "source": "zora",
                    "is_test": True,
                    "_original": None,
                }
            )

        log.info(f"🧪 Generated {len(msgs)} Zora test messages")
        return msgs


# Factory
def create_zora_chat_service(
    username: Optional[str] = None, on_message_callback: Optional[Callable] = None
) -> ZoraChatService:
    return ZoraChatService(username=username, on_message_callback=on_message_callback)
