"""
Tweet Generator Service for Pokemon LLM Agent.

Orchestrates the tweet generation flow:
1. Generate image via ComfyUI (with achievement-specific prompts)
2. Generate tweet text via LLM
3. Send to Chronicle as a DRAFT for Admin approval

Note: Discord approval and direct Twitter posting have been replaced by Chronicle Drafts.
"""

import asyncio
import os
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict, List

from services.comfyui_image_service import ComfyUIImageService, create_image_service
from core.chronicle_client import get_chronicle_client

# Discord and Twitter services removed/deprecated
from trackers.achievement_tracker import (
    Achievement,
    AchievementType,
    AchievementImagePrompt,
    ACHIEVEMENT_IMAGE_PROMPTS,
)

log = logging.getLogger("tweet_generator")

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    log.warning("httpx not installed. Chronicle integration disabled.")


class TweetGeneratorResult(Enum):
    """Final result of the tweet generation process."""

    POSTED = "posted"  # Successfully sent to Chronicle as Draft
    DENIED = "denied"  # Deprecated
    TIMEOUT = "timeout"  # Deprecated
    MAX_REGENERATIONS = "max_regenerations"  # Hit max regeneration limit
    DISABLED = "disabled"  # Service disabled
    ERROR = "error"  # Error during process


@dataclass
class TweetGeneratorOutcome:
    """Outcome of the tweet generation process."""

    result: TweetGeneratorResult
    achievement_type: Optional[AchievementType] = None
    tweet_text: Optional[str] = None
    image_path: Optional[str] = None
    tweet_url: Optional[str] = None  # Will be None for drafts
    regeneration_count: int = 0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TweetGenerator:
    """
    Orchestrates tweet generation with image and text, sending to Chronicle as a draft.
    """

    def __init__(
        self,
        image_service: ComfyUIImageService = None,
        twitter_service: Any = None,  # Kept for signature compatibility
        discord_service: Any = None,  # Kept for signature compatibility
        llm_client: Any = None,
    ):
        """
        Initialize the tweet generator.
        """
        self.image_service = image_service or create_image_service()
        self.llm_client = llm_client
        self.chronicle_client = get_chronicle_client()
        self.enabled = True  # Always enabled now, handled by client

        log.info("Tweet Generator initialized with Chronicle Client")

    async def generate_and_post_achievement_tweet(
        self,
        achievement: Achievement,
        run_state: Any = None,
        game_state: dict = None,
        screenshot_path: str = None,
    ) -> TweetGeneratorOutcome:
        """
        Generate content and send to Chronicle as a draft.

        Args:
            achievement: The achievement that triggered this tweet
            run_state: RunState object with run context
            game_state: Current game state dict
            screenshot_path: Path to the current game screenshot (optional)

        Returns:
            TweetGeneratorOutcome with result and details
        """
        if not self.enabled:
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.DISABLED,
                achievement_type=achievement.achievement_type,
                error="Tweet generation is disabled",
            )

        # Get achievement-specific image prompt
        image_prompt = ACHIEVEMENT_IMAGE_PROMPTS.get(
            achievement.achievement_type,
            AchievementImagePrompt(positive_prompt="", scene_description=""),
        )

        # Build run context
        run_context = self._build_run_context(
            is_continuing_run=True,
            run_state=run_state,
            game_state=game_state,
            achievement=achievement,
        )

        current_image_path = None
        current_tweet_text = None

        try:
            # 1. Generate Image
            log.info(
                f"Generating tweet image for {achievement.achievement_type.value}..."
            )
            current_image_path = await self.image_service.generate_image(
                positive_prompt_addition=image_prompt.positive_prompt,
                negative_prompt_addition=image_prompt.negative_prompt,
            )

            if not current_image_path:
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.ERROR,
                    achievement_type=achievement.achievement_type,
                    error="Failed to generate image",
                )

            # 2. Generate Text
            log.info("Generating tweet text...")
            current_tweet_text = await self._generate_achievement_tweet_text(
                achievement, run_state, game_state
            )

            if not current_tweet_text:
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.ERROR,
                    achievement_type=achievement.achievement_type,
                    image_path=current_image_path,
                    error="Failed to generate tweet text",
                )

            # 3. Send to Chronicle as Draft
            log.info("Sending draft to Chronicle...")
            success = await self._send_to_chronicle(
                tweet_text=current_tweet_text,
                image_path=current_image_path,
                achievement=achievement,
                run_context=run_context,
                screenshot_path=screenshot_path,
            )

            if success:
                log.info(
                    f"✅ Tweet draft created in Chronicle for {achievement.achievement_type.value}"
                )
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.POSTED,
                    achievement_type=achievement.achievement_type,
                    tweet_text=current_tweet_text,
                    image_path=current_image_path,
                    tweet_url="chronicle-draft",  # Placeholder
                )
            else:
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.ERROR,
                    achievement_type=achievement.achievement_type,
                    tweet_text=current_tweet_text,
                    image_path=current_image_path,
                    error="Failed to send draft to Chronicle",
                )

        except Exception as e:
            log.error(f"Tweet generation error: {e}")
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.ERROR,
                achievement_type=achievement.achievement_type,
                error=str(e),
            )

    async def generate_and_post_tweet(
        self,
        is_continuing_run: bool,
        run_state: Any = None,
        game_state: dict = None,
    ) -> TweetGeneratorOutcome:
        """
        Generate and post a stream start tweet (no specific achievement).
        """
        # Create a stream start achievement for consistent handling
        stream_achievement = Achievement(
            achievement_type=AchievementType.STREAM_START,
            triggered_at=datetime.now().isoformat(),
            context={"is_continuing": is_continuing_run},
        )

        return await self.generate_and_post_achievement_tweet(
            achievement=stream_achievement,
            run_state=run_state,
            game_state=game_state,
        )

    async def _send_to_chronicle(
        self,
        tweet_text: str,
        image_path: str,
        achievement: Achievement,
        run_context: Dict[str, Any],
        screenshot_path: str = None,
    ) -> bool:
        """Send tweet draft to Chronicle Server."""

        # Prepare attributes from context
        attributes = [
            {"trait_type": "Type", "value": "Tweet Draft"},
            {
                "trait_type": "Achievement",
                "value": achievement.achievement_type.value,
            },
        ]

        # Add simple context fields
        for k, v in run_context.items():
            if isinstance(v, (str, int, float, bool)):
                attributes.append(
                    {"trait_type": k.replace("_", " ").title(), "value": v}
                )

        gallery_paths = []
        # We can also attach the screenshot as a gallery item if available
        if screenshot_path and os.path.exists(screenshot_path):
            gallery_paths.append(screenshot_path)

        success = await self.chronicle_client.create_draft(
            name=f"Tweet: {achievement.get_title()}",
            symbol="TWEET",
            description=tweet_text,
            attributes=attributes,
            image_path=image_path,
            gallery_paths=gallery_paths,
            status="draft",
        )

        return success

    def _build_run_context(
        self,
        is_continuing_run: bool,
        run_state: Any = None,
        game_state: dict = None,
        achievement: Achievement = None,
    ) -> Dict[str, Any]:
        """Build run context dict."""
        context = {
            "is_continuing": is_continuing_run,
        }

        # Add achievement info
        if achievement:
            context["achievement"] = achievement.achievement_type.value
            if achievement.context:
                # Merge achievement context
                context.update(achievement.context)

        if game_state:
            # Location
            map_name = game_state.get("map_name", "")
            if map_name:
                context["location"] = map_name.replace("_", " ").title()

            # Badges
            badges = game_state.get("badges", [])
            if isinstance(badges, list):
                context["badges"] = len(badges)
            else:
                context["badges"] = badges

        if run_state:
            # Playtime
            elapsed = getattr(run_state, "elapsed_seconds", 0)
            if elapsed:
                hours = elapsed / 3600
                context["playtime"] = f"{hours:.1f} hours"

        return context

    async def _generate_achievement_tweet_text(
        self,
        achievement: Achievement,
        run_state: Any = None,
        game_state: dict = None,
    ) -> Optional[str]:
        """Generate tweet text for a specific achievement."""
        if not self.llm_client:
            log.warning("No LLM client configured for tweet generation")
            return self._fallback_achievement_tweet(achievement)

        try:
            from core.prompts import build_achievement_tweet_prompt

            prompt = build_achievement_tweet_prompt(achievement, run_state, game_state)

            # Call LLM
            response = await self._call_llm(prompt)

            if response:
                # Clean up response (remove quotes, extra whitespace)
                tweet_text = response.strip().strip("\"'")

                # Ensure it fits Twitter limit
                if len(tweet_text) > 280:
                    tweet_text = tweet_text[:277] + "..."

                return tweet_text

        except ImportError:
            log.warning("Achievement tweet prompt not found, using fallback")
        except Exception as e:
            log.error(f"LLM tweet generation failed: {e}")

        return self._fallback_achievement_tweet(achievement)

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM to generate text."""
        if not self.llm_client:
            return None

        try:
            # Handle different LLM client types
            if hasattr(self.llm_client, "chat"):
                # OpenAI-style client (synchronous)
                response = self.llm_client.chat.completions.create(
                    model=os.getenv("Z_AI_MODEL", "glm-4.6"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.8,
                )
                return response.choices[0].message.content
            elif callable(self.llm_client):
                # Simple callable client
                result = self.llm_client(prompt)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            else:
                log.warning(f"Unknown LLM client type: {type(self.llm_client)}")
                return None
        except Exception as e:
            log.error(f"LLM call failed: {e}")
            return None

    def _fallback_achievement_tweet(
        self,
        achievement: Achievement,
    ) -> str:
        """Generate fallback tweet text for an achievement."""
        # Simple fallback map
        return f"Just achieved {achievement.achievement_type.value}! #PokemonRed #LassPlaysPokemon"


def create_tweet_generator(llm_client: Any = None) -> TweetGenerator:
    """Factory function to create a TweetGenerator instance."""
    return TweetGenerator(llm_client=llm_client)
