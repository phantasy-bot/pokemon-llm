"""
Discord Approval Service for Pokemon LLM Agent.

Handles posting tweet drafts to Discord for community approval before posting to X.
Uses reaction-based voting for approve/deny/regenerate decisions.
"""

import asyncio
import os
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Awaitable

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
    Discord bot for tweet approval workflow.

    Posts tweet drafts with images to a Discord channel and monitors
    reactions for approve/deny/regenerate decisions.
    """

    # Emoji mappings for approval actions
    EMOJI_APPROVE = "\u2705"  # ✅ Approve and post
    EMOJI_DENY = "\u274c"  # ❌ Deny and skip
    EMOJI_REGENERATE_ALL = "\U0001f504"  # 🔄 Regenerate image + text
    EMOJI_REGENERATE_IMAGE = "\U0001f5bc\ufe0f"  # 🖼️ Regenerate image only
    EMOJI_REGENERATE_TEXT = "\U0001f4dd"  # 📝 Regenerate text only

    EMOJI_TO_ACTION = {
        EMOJI_APPROVE: ApprovalAction.APPROVED,
        EMOJI_DENY: ApprovalAction.DENIED,
        EMOJI_REGENERATE_ALL: ApprovalAction.REGENERATE_ALL,
        EMOJI_REGENERATE_IMAGE: ApprovalAction.REGENERATE_IMAGE,
        EMOJI_REGENERATE_TEXT: ApprovalAction.REGENERATE_TEXT,
    }

    def __init__(
        self,
        bot_token: str = None,
        channel_id: str = None,
        approval_threshold: int = None,
        approval_timeout: int = None,
        max_regenerations: int = None,
    ):
        """
        Initialize the Discord approval service.

        Args:
            bot_token: Discord bot token
            channel_id: Channel ID for posting approval requests
            approval_threshold: Number of approve votes needed (default: 1)
            approval_timeout: Timeout in seconds (default: 900 = 15 min)
            max_regenerations: Max regeneration attempts before auto-skip (default: 3)
        """
        self.bot_token = bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
        self.channel_id = channel_id or os.getenv("DISCORD_APPROVAL_CHANNEL_ID", "")
        self.approval_threshold = int(
            approval_threshold or os.getenv("DISCORD_APPROVAL_THRESHOLD", "1")
        )
        self.approval_timeout = int(
            approval_timeout or os.getenv("DISCORD_APPROVAL_TIMEOUT", "900")
        )
        self.max_regenerations = int(
            max_regenerations or os.getenv("DISCORD_MAX_REGENERATIONS", "3")
        )

        self.enabled = os.getenv("DISCORD_ENABLED", "false").lower() == "true"
        self._bot = None
        self._ready = asyncio.Event()
        self._bot_task: Optional[asyncio.Task] = None

        if self.enabled:
            if self._validate_config():
                log.info(
                    f"Discord Approval Service configured "
                    f"(threshold={self.approval_threshold}, timeout={self.approval_timeout}s)"
                )
            else:
                log.warning("Discord enabled but configuration incomplete")
                self.enabled = False
        else:
            log.info("Discord Approval Service disabled")

    def _validate_config(self) -> bool:
        """Check if all required configuration is present."""
        return bool(self.bot_token and self.channel_id)

    async def start(self):
        """Start the Discord bot in the background."""
        if not self.enabled:
            return

        if self._bot_task is not None:
            return  # Already running

        try:
            import discord
            from discord.ext import commands

            intents = discord.Intents.default()
            intents.message_content = True
            intents.reactions = True

            self._bot = commands.Bot(command_prefix="!", intents=intents)

            @self._bot.event
            async def on_ready():
                log.info(f"Discord bot connected as {self._bot.user}")
                self._ready.set()

            # Run bot in background
            self._bot_task = asyncio.create_task(self._bot.start(self.bot_token))

            # Wait for bot to be ready (with timeout)
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                log.error("Discord bot failed to connect within 30 seconds")
                self.enabled = False

        except ImportError:
            log.error("discord.py not installed. Run: pip install discord.py")
            self.enabled = False
        except Exception as e:
            log.error(f"Failed to start Discord bot: {e}")
            self.enabled = False

    async def stop(self):
        """Stop the Discord bot."""
        if self._bot:
            await self._bot.close()
        if self._bot_task:
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass
        self._ready.clear()

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

        Args:
            tweet_text: The proposed tweet text
            image_path: Path to the generated AI image
            run_context: Context dict with run info (is_continuing, location, team, etc.)
            regeneration_count: Current regeneration attempt number
            screenshot_path: Path to the game screenshot (optional)

        Returns:
            ApprovalResult with the chosen action
        """
        if not self.enabled:
            return ApprovalResult(
                action=ApprovalAction.DENIED, error="Discord service is disabled"
            )

        # Ensure bot is running
        if not self._ready.is_set():
            await self.start()

        if not self._ready.is_set():
            return ApprovalResult(
                action=ApprovalAction.DENIED, error="Discord bot not connected"
            )

        try:
            import discord
            import os

            channel = self._bot.get_channel(int(self.channel_id))
            if not channel:
                channel = await self._bot.fetch_channel(int(self.channel_id))

            if not channel:
                return ApprovalResult(
                    action=ApprovalAction.DENIED,
                    error=f"Could not find channel: {self.channel_id}",
                )

            run_context = run_context or {}

            # Build the embed
            embed = self._build_approval_embed(
                tweet_text, run_context, regeneration_count
            )

            # Collect files to send
            files = []

            # Add game screenshot first if available
            if screenshot_path and os.path.exists(screenshot_path):
                files.append(
                    discord.File(screenshot_path, filename="game_screenshot.png")
                )
                embed.add_field(
                    name="Game Screenshot",
                    value="See attached game screenshot below",
                    inline=False,
                )

            # Add AI-generated image
            if image_path and os.path.exists(image_path):
                files.append(discord.File(image_path, filename="ai_generated.png"))
                # Set the AI image as the embed thumbnail (main display)
                embed.set_image(url="attachment://ai_generated.png")

            if not files:
                # No images to send
                log.warning("No images available for approval request")

            message = await channel.send(embed=embed, files=files if files else None)

            # Add reaction emojis
            for emoji in self.EMOJI_TO_ACTION.keys():
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    log.warning(f"Failed to add reaction {emoji}: {e}")

            log.info(f"Posted approval request: {message.id} with {len(files)} images")

            # Wait for votes
            result = await self._wait_for_votes(message)

            # Update message with result
            await self._update_message_with_result(message, result)

            return result

        except Exception as e:
            log.error(f"Error in approval request: {e}")
            return ApprovalResult(action=ApprovalAction.DENIED, error=str(e))

    def _build_approval_embed(
        self,
        tweet_text: str,
        run_context: dict,
        regeneration_count: int,
    ):
        """Build a Discord embed for the approval request."""
        import discord

        is_continuing = run_context.get("is_continuing", False)
        status = "Continuing Run" if is_continuing else "Fresh Start"

        embed = discord.Embed(
            title="\U0001f426 Tweet Approval Request",  # 🐦
            color=discord.Color.blue(),
        )

        # Tweet text
        embed.add_field(
            name="Tweet Text",
            value=f"```{tweet_text}```",
            inline=False,
        )

        # Character count
        char_count = len(tweet_text)
        char_status = "\u2705" if char_count <= 280 else "\u26a0\ufe0f"
        embed.add_field(
            name="Characters",
            value=f"{char_status} {char_count}/280",
            inline=True,
        )

        # Run context
        context_lines = [f"\u2022 **Status**: {status}"]
        if run_context.get("location"):
            context_lines.append(f"\u2022 **Location**: {run_context['location']}")
        if run_context.get("team"):
            context_lines.append(f"\u2022 **Team**: {run_context['team']}")
        if run_context.get("badges") is not None:
            context_lines.append(f"\u2022 **Badges**: {run_context['badges']}")
        if run_context.get("playtime"):
            context_lines.append(f"\u2022 **Playtime**: {run_context['playtime']}")

        embed.add_field(
            name="Run Context",
            value="\n".join(context_lines),
            inline=False,
        )

        # Regeneration status
        if regeneration_count > 0:
            embed.add_field(
                name="Regeneration",
                value=f"Attempt {regeneration_count}/{self.max_regenerations}",
                inline=True,
            )

        # Instructions
        instructions = (
            f"{self.EMOJI_APPROVE} **Approve** ({self.approval_threshold} needed)\n"
            f"{self.EMOJI_DENY} **Deny** (skip this tweet)\n"
            f"{self.EMOJI_REGENERATE_ALL} **Regen All** (new image + text)\n"
            f"{self.EMOJI_REGENERATE_IMAGE} **Regen Image** (keep text)\n"
            f"{self.EMOJI_REGENERATE_TEXT} **Regen Text** (keep image)"
        )
        embed.add_field(
            name="React to Approve/Deny",
            value=instructions,
            inline=False,
        )

        embed.set_footer(text=f"Timeout: {self.approval_timeout // 60} minutes")

        return embed

    async def _wait_for_votes(self, message) -> ApprovalResult:
        """Wait for reactions and determine the result."""
        import discord

        start_time = asyncio.get_event_loop().time()
        check_interval = 2.0  # Check every 2 seconds

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self.approval_timeout:
                return ApprovalResult(
                    action=ApprovalAction.TIMEOUT,
                    message_id=message.id,
                )

            # Refresh message to get current reactions
            try:
                message = await message.channel.fetch_message(message.id)
            except Exception as e:
                log.warning(f"Failed to refresh message: {e}")
                await asyncio.sleep(check_interval)
                continue

            # Count reactions (excluding bot's own reactions)
            reaction_counts = {}
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)
                if emoji_str in self.EMOJI_TO_ACTION:
                    # Subtract 1 for the bot's own reaction
                    count = reaction.count - 1
                    if count > 0:
                        reaction_counts[emoji_str] = count

            # Priority: DENY > REGENERATE > APPROVE
            if self.EMOJI_DENY in reaction_counts:
                return ApprovalResult(
                    action=ApprovalAction.DENIED,
                    vote_count=reaction_counts[self.EMOJI_DENY],
                    message_id=message.id,
                )

            if self.EMOJI_REGENERATE_ALL in reaction_counts:
                return ApprovalResult(
                    action=ApprovalAction.REGENERATE_ALL,
                    vote_count=reaction_counts[self.EMOJI_REGENERATE_ALL],
                    message_id=message.id,
                )

            if self.EMOJI_REGENERATE_IMAGE in reaction_counts:
                return ApprovalResult(
                    action=ApprovalAction.REGENERATE_IMAGE,
                    vote_count=reaction_counts[self.EMOJI_REGENERATE_IMAGE],
                    message_id=message.id,
                )

            if self.EMOJI_REGENERATE_TEXT in reaction_counts:
                return ApprovalResult(
                    action=ApprovalAction.REGENERATE_TEXT,
                    vote_count=reaction_counts[self.EMOJI_REGENERATE_TEXT],
                    message_id=message.id,
                )

            if reaction_counts.get(self.EMOJI_APPROVE, 0) >= self.approval_threshold:
                return ApprovalResult(
                    action=ApprovalAction.APPROVED,
                    vote_count=reaction_counts[self.EMOJI_APPROVE],
                    message_id=message.id,
                )

            await asyncio.sleep(check_interval)

    async def _update_message_with_result(self, message, result: ApprovalResult):
        """Update the Discord message with the final result."""
        import discord

        action_text = {
            ApprovalAction.APPROVED: "\u2705 **APPROVED** - Posting to X...",
            ApprovalAction.DENIED: "\u274c **DENIED** - Tweet skipped",
            ApprovalAction.REGENERATE_ALL: "\U0001f504 **REGENERATING** - New image + text",
            ApprovalAction.REGENERATE_IMAGE: "\U0001f5bc\ufe0f **REGENERATING IMAGE** - Keeping text",
            ApprovalAction.REGENERATE_TEXT: "\U0001f4dd **REGENERATING TEXT** - Keeping image",
            ApprovalAction.TIMEOUT: "\u23f0 **TIMEOUT** - No decision made",
        }

        try:
            # Get the existing embed and update it
            embed = message.embeds[0] if message.embeds else discord.Embed()
            embed.color = (
                discord.Color.green()
                if result.action == ApprovalAction.APPROVED
                else discord.Color.red()
                if result.action == ApprovalAction.DENIED
                else discord.Color.orange()
            )
            embed.set_footer(text=action_text.get(result.action, "Unknown result"))

            await message.edit(embed=embed)
        except Exception as e:
            log.warning(f"Failed to update message with result: {e}")


def create_discord_service() -> DiscordApprovalService:
    """Factory function to create a Discord approval service instance."""
    return DiscordApprovalService()
