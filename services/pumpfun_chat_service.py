# --- pumpfun_chat_service.py ---
"""
Pump.fun Livestream Chat Service for Pokemon LLM Agent.
Connects to pump.fun token chat rooms via WebSocket to read and respond to viewer messages.
Based on analysis of pump-chat-client (https://github.com/codingbutter/pump-chat-client).

This is a Python native implementation of the pump.fun chat WebSocket protocol.
"""

import asyncio
import json
import logging
import time
import random
from dataclasses import dataclass
from typing import List, Optional, Callable, Any
from collections import deque
import os

log = logging.getLogger("pumpfun_chat")

# Check if websockets is available
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    log.warning("websockets not installed. Pump.fun chat integration disabled. Install with: pip install websockets")

# Configuration
PUMPFUN_WS_URL = "wss://livechat.pump.fun/socket.io/?EIO=4&transport=websocket"
PUMPFUN_ORIGIN = "https://pump.fun"

# Test mode configuration
# Test mode configuration
CHAT_TEST_MODE = os.getenv("CHAT_TEST_MODE", "false").lower() == "true"

# Test mode usernames and message templates
TEST_USERNAMES = [
    "DiamondHands", "PaperHands42", "SolanaShill", "MoonBoi", "RugPullVictim",
    "DexScreener", "PumpItUp", "JeetSlayer", "WhaleWatcher", "ApeInNow",
    "ToTheMoon", "BondingCurve", "LiquidityKing", "SolanaMaxi", "MemeCoinKid"
]

TEST_MESSAGES = [
    # Hype messages
    "LFG! 🚀", "TO THE MOON!", "APE IN!", "diamond hands only 💎🙌",
    "this is going to 100x", "who else is watching this?", "based dev",
    # Questions
    "wen moon?", "is this rug?", "who made this?", "what's the market cap?",
    "how long you been playing?", "are you an AI?", "this is wild lol",
    # Engagement
    "love the stream!", "keep it up!", "this is hilarious", "based ai gamer",
    "finally something different", "pokemon ai is the future", "GG",
    # Crypto slang
    "WAGMI", "NGMI if you sell", "jeets out", "paper hands crying rn",
    "whales loading up", "bonding curve looking good", "bullish af",
    # More variety
    "dev is based", "voice chat when?", "chart looks healthy", "dip bought",
    "don't fade this", "early entry", "checking solscan", "volume picking up",
    "send it higher", "waiting for raydium", "LFG guys", "hold the line"
]


@dataclass
class PumpFunMessage:
    """Represents a chat message from pump.fun."""
    id: str
    room_id: str
    username: str
    user_address: str
    message: str
    profile_image: str
    timestamp: str
    message_type: str
    expires_at: int
    responded: bool = False
    is_test: bool = False


class PumpFunChatService:
    """
    Manages pump.fun livestream chat connection for the Pokemon LLM agent.
    
    Features:
    - Connects to pump.fun token chat rooms via WebSocket
    - Maintains message queue with timestamps
    - Provides API for getting pending/past messages
    - Sends responses back to chat (requires auth)
    """
    
    def __init__(
        self,
        token_address: str = None,
        username: str = "LassAI",
        on_message_callback: Optional[Callable] = None,
        message_history_limit: int = 100
    ):
        """
        Initialize the pump.fun chat service.
        
        Args:
            token_address: The pump.fun token address to connect to
            username: Display name for the bot (used when sending messages)
            on_message_callback: Optional callback when a message is received
            message_history_limit: Maximum messages to store in memory
        """
        self.token_address = token_address or os.getenv("PUMPFUN_TOKEN_ADDRESS", "")
        self.cookie = os.getenv("PUMPFUN_COOKIE", "")
        self.username = username
        self.on_message_callback = on_message_callback
        self.message_history_limit = message_history_limit
        
        # Connection state
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        # Message storage
        self._message_queue: deque[PumpFunMessage] = deque(maxlen=message_history_limit)
        self._last_commentary_timestamp: float = 0
        
        # Socket.IO protocol state
        self._ack_id = 0
        self._ping_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        
        # Test mode
        self._test_mode = CHAT_TEST_MODE
        
        # Validate configuration
        self._is_configured = bool(self.token_address)
        
        if self._test_mode:
            log.info("🧪 Pump.fun TEST MODE enabled! Will generate fake messages")
        elif not self._is_configured:
            log.warning("Pump.fun chat not configured. Set PUMPFUN_TOKEN_ADDRESS in .env")
        elif not WEBSOCKETS_AVAILABLE:
            log.warning("websockets not available. Install with: pip install websockets")
    
    @property
    def is_available(self) -> bool:
        """Check if pump.fun chat service is available (real or test mode)."""
        if self._test_mode:
            return True
        return WEBSOCKETS_AVAILABLE and self._is_configured
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected to pump.fun chat."""
        return self._connected
    
    async def start(self) -> bool:
        """
        Start the pump.fun chat client.
        Returns True if started successfully, False otherwise.
        """
        if not self.is_available:
            log.warning("Cannot start pump.fun chat - not available or not configured")
            return False
        
        if self._running:
            log.info("Pump.fun chat service already running")
            return True
        
        self._running = True
        
        if not self._test_mode:
            # Start connection task
            asyncio.create_task(self._connect_loop())
        
        log.info(f"Pump.fun chat service started for token: {self.token_address}")
        return True
    
    async def _connect_loop(self):
        """Main connection loop with reconnection logic."""
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                log.error(f"Pump.fun connection error: {e}")
                self._connected = False
                
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    self._reconnect_attempts += 1
                    delay = min(2 ** self._reconnect_attempts, 30)
                    log.info(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts})...")
                    await asyncio.sleep(delay)
                else:
                    log.error("Max reconnection attempts reached")
                    break
    
    async def _connect(self):
        """Establish WebSocket connection to pump.fun chat."""
        headers = {
            "Host": "livechat.pump.fun",
            "Origin": PUMPFUN_ORIGIN,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        if self.cookie:
            headers["Cookie"] = self.cookie
        else:
            log.warning("⚠️ No PUMPFUN_COOKIE provided. Sending messages will likely fail.")
        
        log.info(f"Connecting to pump.fun chat: {self.token_address}")
        
        async with websockets.connect(PUMPFUN_WS_URL, extra_headers=headers) as ws:
            self._ws = ws
            self._reconnect_attempts = 0
            
            # Handle incoming messages
            async for message in ws:
                await self._handle_message(message)
    
    async def _handle_message(self, data: str):
        """
        Handle incoming WebSocket messages using Socket.IO protocol.
        Socket.IO message types:
        - 0: Open (connection established)
        - 40: Connect acknowledgment  
        - 42: Event message
        - 43: Event with acknowledgment
        - 2: Ping
        - 3: Pong
        """
        if not data:
            return
        
        # Extract message type (numeric prefix)
        msg_type = ""
        for char in data:
            if char.isdigit():
                msg_type += char
            else:
                break
        
        if msg_type == "0":
            # Connection open - parse config and send handshake
            await self._handle_connect(data)
        
        elif msg_type == "40":
            # Connected acknowledgment - join the room
            await self._handle_connected_ack()
        
        elif msg_type == "42":
            # Event message
            await self._handle_event(data)
        
        elif msg_type.startswith("43"):
            # Numbered acknowledgment
            await self._handle_numbered_ack(data)
        
        elif msg_type == "2":
            # Ping from server - send pong
            await self._send("3")
        
        elif msg_type == "3":
            # Pong response - connection alive
            pass
    
    async def _handle_connect(self, data: str):
        """Handle connection open message."""
        try:
            json_data = json.loads(data[1:])
            ping_interval = json_data.get("pingInterval", 25000)
            
            # Start ping loop
            if self._ping_task:
                self._ping_task.cancel()
            self._ping_task = asyncio.create_task(self._ping_loop(ping_interval / 1000))
            
            # Send handshake
            handshake = json.dumps({
                "origin": PUMPFUN_ORIGIN,
                "timestamp": int(time.time() * 1000),
                "token": None
            })
            await self._send(f"40{handshake}")
            
        except Exception as e:
            log.error(f"Error handling connect: {e}")
    
    async def _handle_connected_ack(self):
        """Handle connection acknowledgment - join the room."""
        self._connected = True
        log.info("Connected to pump.fun chat server")
        
        # Join the room
        ack_id = self._get_next_ack_id()
        join_msg = json.dumps(["joinRoom", {
            "roomId": self.token_address,
            "username": self.username
        }])
        await self._send(f"42{ack_id}{join_msg}")
    
    async def _handle_event(self, data: str):
        """Handle event messages (new messages, etc)."""
        try:
            # Remove "42" prefix and parse
            event_data = json.loads(data[2:])
            event_name = event_data[0]
            payload = event_data[1] if len(event_data) > 1 else None
            
            if event_name == "setCookie":
                # After cookie, request message history
                await self._request_message_history()
            
            elif event_name == "newMessage":
                await self._handle_new_message(payload)
            
            elif event_name == "userLeft":
                log.debug(f"User left: {payload}")
            
        except Exception as e:
            log.error(f"Error handling event: {e}")
    
    async def _handle_numbered_ack(self, data: str):
        """Handle numbered acknowledgment messages."""
        try:
            # Extract ack ID and parse response
            msg_type = data[:3]  # e.g., "431"
            response_data = json.loads(data[3:])
            
            # Check for message history response
            if isinstance(response_data, list) and len(response_data) > 0:
                messages = response_data[0]
                if isinstance(messages, list):
                    log.info(f"Received {len(messages)} historical messages")
                    for msg in messages:
                        await self._handle_new_message(msg, is_history=True)
            
        except Exception as e:
            log.error(f"Error handling numbered ack: {e}")
    
    async def _handle_new_message(self, msg_data: dict, is_history: bool = False):
        """Process a new chat message."""
        try:
            message = PumpFunMessage(
                id=msg_data.get("id", ""),
                room_id=msg_data.get("roomId", ""),
                username=msg_data.get("username", "anonymous"),
                user_address=msg_data.get("userAddress", ""),
                message=msg_data.get("message", ""),
                profile_image=msg_data.get("profile_image", ""),
                timestamp=msg_data.get("timestamp", ""),
                message_type=msg_data.get("messageType", ""),
                expires_at=msg_data.get("expiresAt", 0)
            )
            
            self._message_queue.append(message)
            
            if not is_history:
                log.info(f"💬 Pump.fun [{message.username}]: {message.message}")
                
                if self.on_message_callback:
                    try:
                        self.on_message_callback(message)
                    except Exception as e:
                        log.error(f"Error in message callback: {e}")
            
        except Exception as e:
            log.error(f"Error processing message: {e}")
    
    async def _request_message_history(self):
        """Request message history from the server."""
        ack_id = self._get_next_ack_id()
        history_msg = json.dumps(["getMessageHistory", {
            "roomId": self.token_address,
            "before": None,
            "limit": self.message_history_limit
        }])
        await self._send(f"42{ack_id}{history_msg}")
    
    async def _ping_loop(self, interval: float):
        """Send periodic pings to keep connection alive."""
        while self._running and self._ws:
            try:
                await asyncio.sleep(interval)
                await self._send("2")
            except Exception:
                break
    
    async def _send(self, data: str):
        """Send data through WebSocket."""
        if self._ws:
            try:
                await self._ws.send(data)
            except Exception as e:
                log.error(f"Error sending: {e}")
    
    def _get_next_ack_id(self) -> int:
        """Get next acknowledgment ID (cycles 0-9)."""
        ack_id = self._ack_id
        self._ack_id = (self._ack_id + 1) % 10
        return ack_id
    
    async def stop(self):
        """Stop the pump.fun chat client."""
        self._running = False
        self._connected = False
        
        if self._ping_task:
            self._ping_task.cancel()
        
        if self._ws:
            await self._ws.close()
        
        log.info("Pump.fun chat service stopped")
    
    def mark_commentary_timestamp(self):
        """Mark the current time as when the last game commentary was sent."""
        self._last_commentary_timestamp = time.time()
    
    def get_messages_for_cycle(self) -> List[dict]:
        """
        Get all messages since the last commentary timestamp.
        Returns messages as dicts for compatibility with chat_response_service.
        """
        cutoff = self._last_commentary_timestamp
        
        messages = [
            msg for msg in self._message_queue
            if not msg.responded and time.time() - self._parse_timestamp(msg.timestamp) > 0
        ]
        
        # Sort oldest first
        messages.sort(key=lambda m: m.timestamp)
        
        return [
            {
                "username": msg.username,
                "display_name": msg.username,
                "message": msg.message,
                "timestamp": self._parse_timestamp(msg.timestamp),
                "user_address": msg.user_address,  # Solana wallet for whale detection
                "is_whale": False,  # TODO: Query token balance to determine whale status
                "_original": msg,
                "source": "pumpfun"
            }
            for msg in messages[-20:]  # Last 20 messages
        ]
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse ISO timestamp to epoch seconds."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.timestamp()
        except:
            return time.time()
    
    def generate_test_messages(self, count: int = 5) -> List[dict]:
        """Generate fake test messages for development/testing."""
        test_messages = []
        base_time = time.time()
        
        for i in range(count):
            username = random.choice(TEST_USERNAMES)
            message = random.choice(TEST_MESSAGES)
            timestamp = base_time - (count - i) * 0.5
            # Randomly make some test users "whales" (20% chance)
            is_whale = random.random() < 0.2
            
            test_messages.append({
                "username": username,
                "display_name": username,
                "message": message,
                "timestamp": timestamp,
                "user_address": f"fake_wallet_{username}",  # Fake address for testing
                "is_whale": is_whale,
                "_original": None,
                "is_test": True,
                "source": "pumpfun"
            })
        
        log.info(f"🧪 Generated {count} pump.fun test messages")
        return test_messages
    
    def generate_single_test_message(self) -> dict:
        """Generate a single random test message."""
        username = random.choice(TEST_USERNAMES)
        message = random.choice(TEST_MESSAGES)
        # Randomly make some test users "whales" (20% chance)
        is_whale = random.random() < 0.2
        
        return {
            "username": username,
            "display_name": username,
            "message": message,
            "timestamp": time.time(),
            "user_address": f"fake_wallet_{username}",
            "is_whale": is_whale,
            "_original": None,
            "is_test": True,
            "source": "pumpfun"
        }
    
    def get_messages_for_cycle_or_test(self) -> List[dict]:
        """Get messages for the current cycle, using test messages if enabled."""
        if CHAT_TEST_MODE:
            return self.generate_test_messages()
        else:
            return self.get_messages_for_cycle()
    
    async def send_message(self, message: str) -> bool:
        """
        Send a message to the pump.fun chat.
        Note: Requires authentication to work.
        
        Args:
            message: The message text to send
            
        Returns:
            True if sent (may not be delivered without auth), False on error
        """
        if not self._connected or not self._ws:
            log.warning("Cannot send message - not connected")
            return False
        
        try:
            ack_id = self._get_next_ack_id()
            send_msg = json.dumps(["sendMessage", {
                "roomId": self.token_address,
                "message": message,
                "username": self.username
            }])
            await self._send(f"42{ack_id}{send_msg}")
            log.info(f"📤 Sent to pump.fun: {message}")
            return True
        except Exception as e:
            log.error(f"Error sending message: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "running": self._running,
            "connected": self._connected,
            "token": self.token_address,
            "total_messages": len(self._message_queue),
            "reconnect_attempts": self._reconnect_attempts
        }


# Factory function
def create_pumpfun_service(
    token_address: str = None,
    username: str = "LassAI",
    on_message_callback: Optional[Callable] = None
) -> PumpFunChatService:
    """
    Factory function to create a PumpFunChatService instance.
    Uses environment variables if parameters not provided.
    """
    return PumpFunChatService(
        token_address=token_address,
        username=username,
        on_message_callback=on_message_callback
    )
