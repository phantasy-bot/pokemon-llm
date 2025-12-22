"""
Discord Approval Service for Pokemon LLM Agent.

DEPRECATED: This service is being obsoleted in favor of the Chronicle Admin Panel.
Approvals now happen via the Admin Panel (Drafts).
"""

import asyncio
import os
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger("discord_service")


class ApprovalAction(Enum):
    """Possible approval actions from Discord reactions."""

    APPROVED = "approved"
    DENIED = "denied"
    REGENERATE_ALL = "regenerate_all"
    REGENERATE_IMAGE = "regenerate_image"
    REGENERATE_TEXT = "regenerate_text"
    TIMEOUT = "timeout"


@dataclass
class ApprovalResult:
    """Result of a Discord approval request."""

    action: ApprovalAction
    vote_count: int = 0
    message_id: Optional[int] = None
    error: Optional[str] = None


class DiscordApprovalService:
    """
    DEPRECATED: Discord bot for tweet approval workflow.
    This service is now a stub.
    """

    def __init__(
        self,
        bot_token: str = None,
        channel_id: str = None,
        approval_threshold: int = None,
        approval_timeout: int = None,
        max_regenerations: int = None,
    ):
        self.enabled = False
        log.info("Discord Approval Service is DEPRECATED and disabled.")

    async def start(self):
        """Start the Discord bot in the background."""
        pass

    async def stop(self):
        """Stop the Discord bot."""
        pass

    async def request_approval(
        self,
        tweet_text: str,
        image_path: str = None,
        run_context: dict = None,
        regeneration_count: int = 0,
        screenshot_path: str = None,
    ) -> ApprovalResult:
        """
        Post a tweet draft to Discord and wait for approval.
        DEPRECATED: Always returns DENIED.
        """
        log.warning("Called request_approval on deprecated Discord service.")
        return ApprovalResult(
            action=ApprovalAction.DENIED, error="Discord service is deprecated"
        )


def create_discord_service() -> DiscordApprovalService:
    """Factory function to create a Discord approval service instance."""
    return DiscordApprovalService()
