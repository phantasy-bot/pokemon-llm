# --- twitch_chat_service.py ---
"""
Twitch Chat Service for Pokemon LLM Agent.
Connects to Twitch IRC chat via twitchio library to read and respond to viewer messages.
Includes test mode for generating fake messages when TWITCH_TEST_MODE=true.
"""

import asyncio
import os
import logging
import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from collections import deque

log = logging.getLogger("twitch_chat")

# Test mode configuration
TWITCH_TEST_MODE = os.getenv("TWITCH_TEST_MODE", "false").lower() == "true"
TWITCH_TEST_MESSAGES_PER_CYCLE = int(os.getenv("TWITCH_TEST_MESSAGES_PER_CYCLE", "10"))

# Check if twitchio is available
try:
    from twitchio.ext import commands
    TWITCHIO_AVAILABLE = True
except ImportError:
    TWITCHIO_AVAILABLE = False
    log.warning("twitchio not installed. Twitch chat integration disabled. Install with: pip install twitchio")

# Test mode usernames and message templates
TEST_USERNAMES = [
    "PokeFan2024", "ShinyHunter99", "GaryWasHere", "AshKetchumFan", "MistyMain",
    "BrockFan", "TeamRocketBlasting", "PikachuLover", "MewtwoStan", "GottaCatchEmAll",
    "PokemonMaster123", "ViridianCity420", "PalletTownBoy", "EliteFourDan", "GymLeaderSara",
    "RandomViewer42", "TwitchChatter", "PokeNerd", "RetroGamer85", "GenOneForever"
]

TEST_MESSAGES = [
    # Questions about game
    "where are you going?", "what pokemon do you have?", "are you lost lol",
    "have you beaten brock yet?", "when are you catching pikachu?",
    "what's your team?", "how many badges?", "is this your first playthrough?",
    # Greetings
    "hey lass!", "hi!", "just got here what's happening", "love the stream!",
    "first time watching!", "let's gooo", "pog", "HYPE", "hello chat!",
    # Playful roasts
    "you've been stuck here for 10 minutes lmao", "just go left omg",
    "bruh moment", "lass please", "skill issue tbh", "have you tried pressing A?",
    "my grandma could beat this game faster", "literally walking in circles",
    # Pokemon references
    "catch that rattata!", "WILD ENCOUNTER POG", "that pikachu is built different",
    "this is like my childhood", "gen 1 best gen", "squirtle gang",
    "charmander would never", "bulbasaur supremacy",
    # Spam/memes (for SKIP testing)
    "KEKW KEKW KEKW", "!gamble all", "LUL LUL LUL", "Kappa Kappa Kappa",
    "asdfghjkl", "zzzzzzzzz", "first", "sub to my channel",
    # Genuine engagement
    "you got this!", "let's catch 'em all!", "I believe in you lass!",
    "@Lass you're doing great!", "keep going!", "almost there!",
]


@dataclass
class ChatMessage:
    """Represents a chat message from Twitch."""
    username: str
    display_name: str
    message: str
    timestamp: float
    is_mention: bool = False
    responded: bool = False
    is_test: bool = False  # Flag for test messages


class TwitchChatService:
    """
    Manages Twitch chat connection for the Pokemon LLM agent.
    
    Features:
    - Listens for @mentions of the bot
    - Maintains message queue with timestamps
    - Provides API for getting pending/past messages
    - Sends responses back to Twitch chat
    """
    
    def __init__(
        self,
        bot_username: str = None,
        oauth_token: str = None,
        channel: str = None,
        on_mention_callback: Optional[Callable] = None
    ):
        """
        Initialize the Twitch chat service.
        
        Args:
            bot_username: The bot's Twitch username (e.g., "LassAI")
            oauth_token: OAuth token with chat:read and chat:edit scopes
            channel: The Twitch channel to join
            on_mention_callback: Optional callback when bot is mentioned
        """
        self.bot_username = bot_username or os.getenv("TWITCH_BOT_USERNAME", "")
        self.oauth_token = oauth_token or os.getenv("TWITCH_OAUTH_TOKEN", "")
        self.channel = channel or os.getenv("TWITCH_CHANNEL", "")
        self.on_mention_callback = on_mention_callback
        
        # Message storage
        self._message_queue: deque[ChatMessage] = deque(maxlen=100)  # Last 100 messages
        self._pending_mentions: List[ChatMessage] = []
        self._last_commentary_timestamp: float = 0
        
        # Bot instance
        self._bot: Optional['TwitchBot'] = None
        self._running = False
        
        # Validate configuration
        self._is_configured = bool(self.bot_username and self.oauth_token and self.channel)
        
        # Test mode can work without real Twitch credentials
        self._test_mode = TWITCH_TEST_MODE
        
        if self._test_mode:
            log.info(f"🧪 Twitch TEST MODE enabled! Will generate {TWITCH_TEST_MESSAGES_PER_CYCLE} fake messages per cycle")
        elif not self._is_configured:
            log.warning("Twitch chat not configured. Set TWITCH_BOT_USERNAME, TWITCH_OAUTH_TOKEN, and TWITCH_CHANNEL in .env")
        elif not TWITCHIO_AVAILABLE:
            log.warning("twitchio not available. Install with: pip install twitchio")
    
    @property
    def is_available(self) -> bool:
        """Check if Twitch chat service is available (real or test mode)."""
        # Test mode is always available
        if self._test_mode:
            return True
        return TWITCHIO_AVAILABLE and self._is_configured
    
    async def start(self) -> bool:
        """
        Start the Twitch chat bot.
        Returns True if started successfully, False otherwise.
        """
        if not self.is_available:
            log.warning("Cannot start Twitch chat - not available or not configured")
            return False
        
        if self._running:
            log.info("Twitch chat service already running")
            return True
        
        try:
            self._bot = TwitchBot(
                token=self.oauth_token,
                prefix="!",
                initial_channels=[self.channel],
                service=self
            )
            
            # Start bot in background task
            asyncio.create_task(self._run_bot())
            self._running = True
            log.info(f"Twitch chat service started for channel: {self.channel}")
            return True
            
        except Exception as e:
            log.error(f"Failed to start Twitch chat service: {e}")
            return False
    
    async def _run_bot(self):
        """Run the Twitch bot (internal)."""
        try:
            await self._bot.start()
        except Exception as e:
            log.error(f"Twitch bot error: {e}")
            self._running = False
    
    async def stop(self):
        """Stop the Twitch chat bot."""
        if self._bot:
            try:
                await self._bot.close()
            except Exception as e:
                log.warning(f"Error closing Twitch bot: {e}")
        self._running = False
        log.info("Twitch chat service stopped")
    
    def add_message(self, msg: ChatMessage):
        """Add a message to the queue (called by the bot)."""
        self._message_queue.append(msg)
        
        # Check if it's a mention of the bot
        if self._is_mention(msg.message):
            msg.is_mention = True
            self._pending_mentions.append(msg)
            log.info(f"🔔 Mention detected from @{msg.display_name}: {msg.message}")
            
            if self.on_mention_callback:
                try:
                    self.on_mention_callback(msg)
                except Exception as e:
                    log.error(f"Error in mention callback: {e}")
    
    def _is_mention(self, message: str) -> bool:
        """Check if the message mentions the bot."""
        bot_lower = self.bot_username.lower()
        message_lower = message.lower()
        
        # Check for @mention or just the bot name
        return f"@{bot_lower}" in message_lower or bot_lower in message_lower
    
    def mark_commentary_timestamp(self):
        """Mark the current time as when the last game commentary was sent."""
        self._last_commentary_timestamp = time.time()
        log.debug(f"Commentary timestamp marked: {self._last_commentary_timestamp}")
    
    def get_pending_mentions(self, since_timestamp: float = None) -> List[ChatMessage]:
        """
        Get mentions that haven't been responded to yet.
        
        Args:
            since_timestamp: Only get mentions after this timestamp.
                           If None, uses last commentary timestamp.
        
        Returns:
            List of ChatMessage objects that are mentions and not yet responded.
        """
        cutoff = since_timestamp or self._last_commentary_timestamp
        
        pending = [
            msg for msg in self._pending_mentions
            if not msg.responded and msg.timestamp > cutoff
        ]
        
        return pending
    
    def get_past_messages(self, count: int = 5) -> List[ChatMessage]:
        """
        Get older messages that weren't responded to (for fallback responses).
        
        Args:
            count: Maximum number of messages to return.
        
        Returns:
            List of older ChatMessage objects that are mentions but not responded.
        """
        # Get mentions before the last commentary that weren't responded to
        cutoff = self._last_commentary_timestamp
        
        past = [
            msg for msg in self._pending_mentions
            if not msg.responded and msg.timestamp <= cutoff
        ]
        
        return past[-count:]  # Return most recent 'count' messages
    
    def get_messages_for_cycle(self) -> List[dict]:
        """
        Get all messages since the last commentary timestamp, formatted for processing.
        
        Returns messages as dicts for compatibility with chat_response_service.
        Sorted by timestamp (oldest first).
        
        Returns:
            List of message dicts with username, display_name, message, timestamp
        """
        cutoff = self._last_commentary_timestamp
        
        # Get all messages (not just mentions) since last commentary
        messages = [
            msg for msg in self._message_queue
            if not msg.responded and msg.timestamp > cutoff
        ]
        
        # Sort oldest first
        messages.sort(key=lambda m: m.timestamp)
        
        # Convert to dicts for chat_response_service
        return [
            {
                "username": msg.username,
                "display_name": msg.display_name,
                "message": msg.message,
                "timestamp": msg.timestamp,
                "_original": msg  # Keep reference for marking responded
            }
            for msg in messages
        ]
    
    def generate_test_messages(self, count: int = None) -> List[dict]:
        """
        Generate fake test messages for development/testing.
        
        Args:
            count: Number of messages to generate. Defaults to TWITCH_TEST_MESSAGES_PER_CYCLE.
        
        Returns:
            List of message dicts compatible with chat_response_service.
        """
        if count is None:
            count = TWITCH_TEST_MESSAGES_PER_CYCLE
        
        test_messages = []
        base_time = time.time()
        
        for i in range(count):
            username = random.choice(TEST_USERNAMES)
            message = random.choice(TEST_MESSAGES)
            timestamp = base_time - (count - i) * 0.5  # Stagger timestamps
            
            test_messages.append({
                "username": username.lower(),
                "display_name": username,
                "message": message,
                "timestamp": timestamp,
                "_original": None,  # No original for test messages
                "is_test": True
            })
        
        log.info(f"🧪 Generated {count} test messages for TWITCH_TEST_MODE")
        return test_messages
    
    def get_messages_for_cycle_or_test(self) -> List[dict]:
        """
        Get messages for the current cycle, using test messages if TWITCH_TEST_MODE is enabled.
        
        Returns:
            List of message dicts (real or test) for processing.
        """
        if TWITCH_TEST_MODE:
            return self.generate_test_messages()
        else:
            return self.get_messages_for_cycle()
    
    def mark_responded(self, msg: ChatMessage):
        """Mark a message as responded to."""
        msg.responded = True
    
    async def send_response(self, username: str, message: str) -> bool:
        """
        Send a response to Twitch chat.
        
        Args:
            username: Username to mention in response (without @)
            message: Response message
        
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self._running or not self._bot:
            log.warning("Cannot send response - Twitch bot not running")
            return False
        
        try:
            channel = self._bot.get_channel(self.channel)
            if channel:
                # Format response with @mention
                full_message = f"@{username} {message}"
                await channel.send(full_message)
                log.info(f"💬 Sent to Twitch: {full_message}")
                return True
            else:
                log.warning(f"Channel {self.channel} not found")
                return False
                
        except Exception as e:
            log.error(f"Failed to send Twitch message: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "running": self._running,
            "total_messages": len(self._message_queue),
            "pending_mentions": len([m for m in self._pending_mentions if not m.responded]),
            "last_commentary": self._last_commentary_timestamp
        }


# TwitchIO Bot implementation
if TWITCHIO_AVAILABLE:
    class TwitchBot(commands.Bot):
        """TwitchIO bot that integrates with TwitchChatService."""
        
        def __init__(self, service: TwitchChatService, **kwargs):
            super().__init__(**kwargs)
            self.service = service
        
        async def event_ready(self):
            """Called when the bot is ready."""
            log.info(f"✅ Twitch bot logged in as: {self.nick}")
            log.info(f"📺 Joined channel: {self.service.channel}")
        
        async def event_message(self, message):
            """Called when a message is received."""
            # Ignore bot's own messages
            if message.echo:
                return
            
            # Create ChatMessage object
            chat_msg = ChatMessage(
                username=message.author.name if message.author else "unknown",
                display_name=message.author.display_name if message.author else "Unknown",
                message=message.content,
                timestamp=time.time()
            )
            
            # Add to service queue
            self.service.add_message(chat_msg)
            
            # Handle commands (if any)
            await self.handle_commands(message)
        
        @commands.command(name="ping")
        async def cmd_ping(self, ctx):
            """Simple ping command for testing."""
            await ctx.send(f"Pong! 🏓 @{ctx.author.display_name}")
else:
    # Dummy class if twitchio not available
    class TwitchBot:
        pass


# Convenience function for creating the service
def create_twitch_service(
    bot_username: str = None,
    oauth_token: str = None,
    channel: str = None,
    on_mention_callback: Optional[Callable] = None
) -> TwitchChatService:
    """
    Factory function to create a TwitchChatService instance.
    
    Uses environment variables if parameters not provided.
    """
    return TwitchChatService(
        bot_username=bot_username,
        oauth_token=oauth_token,
        channel=channel,
        on_mention_callback=on_mention_callback
    )
