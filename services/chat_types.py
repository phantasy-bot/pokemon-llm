from dataclasses import dataclass
from enum import Enum
from typing import Optional

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
    is_subscriber: bool = False  # Twitch subscriber status for priority

class MessageDecision(Enum):
    """Decision for how to handle a chat message."""
    SKIP = "skip"
    RESPOND = "respond"

@dataclass
class DecidedMessage:
    """A chat message with a SKIP/RESPOND decision."""
    username: str
    display_name: str
    message: str
    timestamp: float
    decision: MessageDecision
    reason: Optional[str] = None
