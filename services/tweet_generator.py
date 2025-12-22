"""
Tweet Generator Service for Pokemon LLM Agent.

Orchestrates the complete tweet generation flow:
1. Generate image via ComfyUI (with achievement-specific prompts)
2. Generate tweet text via LLM
3. Request approval via Discord
4. Post to X/Twitter if approved

Supports both stream start tweets and achievement-triggered tweets.
"""

import asyncio
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict

from services.comfyui_image_service import ComfyUIImageService, create_image_service
from services.twitter_service import TwitterService, TweetResult, create_twitter_service
from services.discord_service import (
    DiscordApprovalService,
    ApprovalAction,
    ApprovalResult,
    create_discord_service,
)
from trackers.achievement_tracker import (
    Achievement,
    AchievementType,
    AchievementImagePrompt,
    ACHIEVEMENT_IMAGE_PROMPTS,
)

log = logging.getLogger("tweet_generator")


class TweetGeneratorResult(Enum):
    """Final result of the tweet generation process."""

    POSTED = "posted"  # Successfully posted to X
    DENIED = "denied"  # Denied by Discord vote
    TIMEOUT = "timeout"  # Discord approval timed out
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
    tweet_url: Optional[str] = None
    regeneration_count: int = 0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TweetGenerator:
    """
    Orchestrates tweet generation with image, Discord approval, and X posting.
    Supports achievement-specific image prompts and tweet text.
    """

    def __init__(
        self,
        image_service: ComfyUIImageService = None,
        twitter_service: TwitterService = None,
        discord_service: DiscordApprovalService = None,
        llm_client: Any = None,
    ):
        """
        Initialize the tweet generator.

        Args:
            image_service: ComfyUI image generation service
            twitter_service: X/Twitter posting service
            discord_service: Discord approval service
            llm_client: LLM client for generating tweet text
        """
        self.image_service = image_service or create_image_service()
        self.twitter_service = twitter_service or create_twitter_service()
        self.discord_service = discord_service or create_discord_service()
        self.llm_client = llm_client

        self.max_regenerations = int(os.getenv("DISCORD_MAX_REGENERATIONS", "3"))

        # Check if tweet generation is enabled
        self.enabled = self.twitter_service.enabled and self.discord_service.enabled

        if self.enabled:
            log.info("Tweet Generator initialized and enabled")
        else:
            reasons = []
            if not self.twitter_service.enabled:
                reasons.append("Twitter disabled")
            if not self.discord_service.enabled:
                reasons.append("Discord disabled")
            log.info(f"Tweet Generator disabled: {', '.join(reasons)}")

    async def generate_and_post_achievement_tweet(
        self,
        achievement: Achievement,
        run_state: Any = None,
        game_state: dict = None,
        screenshot_path: str = None,
    ) -> TweetGeneratorOutcome:
        """
        Generate and post a tweet for a specific achievement.

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

        # Build run context for display and LLM
        run_context = self._build_run_context(
            is_continuing_run=True,  # Achievements happen during gameplay
            run_state=run_state,
            game_state=game_state,
            achievement=achievement,
        )

        regeneration_count = 0
        current_image_path = None
        current_tweet_text = None
        current_screenshot_path = screenshot_path  # May be regenerated

        # Start Discord bot
        await self.discord_service.start()

        try:
            while regeneration_count <= self.max_regenerations:
                # Generate image if needed (with achievement-specific prompt)
                if current_image_path is None:
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
                            regeneration_count=regeneration_count,
                        )

                # Generate tweet text if needed
                if current_tweet_text is None:
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
                            regeneration_count=regeneration_count,
                        )

                # Request Discord approval
                log.info(
                    f"Requesting Discord approval (attempt {regeneration_count + 1})..."
                )
                approval = await self.discord_service.request_approval(
                    tweet_text=current_tweet_text,
                    image_path=current_image_path,
                    run_context=run_context,
                    regeneration_count=regeneration_count,
                    screenshot_path=current_screenshot_path,
                )

                # Handle approval result
                result = await self._handle_approval(
                    approval=approval,
                    achievement=achievement,
                    current_tweet_text=current_tweet_text,
                    current_image_path=current_image_path,
                    regeneration_count=regeneration_count,
                    screenshot_path=current_screenshot_path,
                )

                if result is not None:
                    return result

                # Handle regeneration requests
                if approval.action == ApprovalAction.REGENERATE_ALL:
                    log.info("Regenerating both image and text...")
                    regeneration_count += 1
                    current_image_path = None
                    current_tweet_text = None
                elif approval.action == ApprovalAction.REGENERATE_IMAGE:
                    log.info("Regenerating image only...")
                    regeneration_count += 1
                    current_image_path = None
                elif approval.action == ApprovalAction.REGENERATE_TEXT:
                    log.info("Regenerating text only...")
                    regeneration_count += 1
                    current_tweet_text = None

            # Hit max regenerations
            log.warning(f"Max regenerations ({self.max_regenerations}) reached")
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.MAX_REGENERATIONS,
                achievement_type=achievement.achievement_type,
                tweet_text=current_tweet_text,
                image_path=current_image_path,
                regeneration_count=regeneration_count,
            )

        except Exception as e:
            log.error(f"Tweet generation error: {e}")
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.ERROR,
                achievement_type=achievement.achievement_type,
                error=str(e),
                regeneration_count=regeneration_count,
            )

        finally:
            # Cleanup generated image after use (posted, denied, timeout, or error)
            if current_image_path:
                self.image_service.cleanup_image(current_image_path)

            # Stop Discord bot
            await self.discord_service.stop()

    async def generate_and_post_tweet(
        self,
        is_continuing_run: bool,
        run_state: Any = None,
        game_state: dict = None,
    ) -> TweetGeneratorOutcome:
        """
        Generate and post a stream start tweet (no specific achievement).

        Args:
            is_continuing_run: Whether this is continuing an existing run
            run_state: RunState object with run context
            game_state: Current game state dict

        Returns:
            TweetGeneratorOutcome with result and details
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

    async def _handle_approval(
        self,
        approval: ApprovalResult,
        achievement: Achievement,
        current_tweet_text: str,
        current_image_path: str,
        regeneration_count: int,
        screenshot_path: str = None,
    ) -> Optional[TweetGeneratorOutcome]:
        """Handle the Discord approval result."""
        if approval.action == ApprovalAction.APPROVED:
            # Post to X with both images (screenshot + AI generated)
            log.info("Tweet approved! Posting to X...")

            # Build image list: screenshot first, then AI generated
            image_paths = []
            if screenshot_path:
                image_paths.append(screenshot_path)
            if current_image_path:
                image_paths.append(current_image_path)

            tweet_result = await self.twitter_service.post_tweet(
                text=current_tweet_text,
                image_paths=image_paths if image_paths else None,
            )

            if tweet_result.success:
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.POSTED,
                    achievement_type=achievement.achievement_type,
                    tweet_text=current_tweet_text,
                    image_path=current_image_path,
                    tweet_url=tweet_result.tweet_url,
                    regeneration_count=regeneration_count,
                )
            else:
                return TweetGeneratorOutcome(
                    result=TweetGeneratorResult.ERROR,
                    achievement_type=achievement.achievement_type,
                    tweet_text=current_tweet_text,
                    image_path=current_image_path,
                    error=f"Failed to post tweet: {tweet_result.error}",
                    regeneration_count=regeneration_count,
                )

        elif approval.action == ApprovalAction.DENIED:
            log.info("Tweet denied by Discord vote")
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.DENIED,
                achievement_type=achievement.achievement_type,
                tweet_text=current_tweet_text,
                image_path=current_image_path,
                regeneration_count=regeneration_count,
            )

        elif approval.action == ApprovalAction.TIMEOUT:
            log.info("Discord approval timed out")
            return TweetGeneratorOutcome(
                result=TweetGeneratorResult.TIMEOUT,
                achievement_type=achievement.achievement_type,
                tweet_text=current_tweet_text,
                image_path=current_image_path,
                regeneration_count=regeneration_count,
            )

        # Return None for regeneration actions (handled by caller)
        return None

    async def _generate_achievement_tweet_text(
        self,
        achievement: Achievement,
        run_state: Any = None,
        game_state: dict = None,
    ) -> Optional[str]:
        """Generate tweet text for a specific achievement."""
        if not self.llm_client:
            log.warning("No LLM client configured for tweet generation")
            return self._fallback_achievement_tweet(achievement, game_state)

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

        return self._fallback_achievement_tweet(achievement, game_state)

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM to generate text."""
        if not self.llm_client:
            return None

        try:
            # Handle different LLM client types
            if hasattr(self.llm_client, "chat"):
                # OpenAI-style client (synchronous)
                response = self.llm_client.chat.completions.create(
                    model=os.getenv("ZAI_MODEL", "glm-4.6"),
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
        game_state: dict = None,
    ) -> str:
        """Generate fallback tweet text for an achievement."""
        achievement_type = achievement.achievement_type
        context = achievement.context or {}

        # Achievement-specific fallback messages
        fallbacks = {
            AchievementType.STREAM_START: (
                "Starting a brand new Pokemon Red adventure! "
                "Watch me explore Kanto and become a Pokemon Master! "
                "#Pokemon #PokemonRed #LLMLetsPlay"
            ),
            AchievementType.FIRST_POKEMON: (
                f"Just got my first Pokemon - {context.get('pokemon', 'a new friend')}! "
                "The adventure begins! #Pokemon #PokemonRed #LLMLetsPlay"
            ),
            AchievementType.ROUTE_1_FLOWER: (
                "Taking a moment to appreciate the beauty of Route 1. "
                "The flowers are lovely this time of year! #Pokemon #PokemonRed"
            ),
            AchievementType.FIRST_CATCH: (
                f"Caught my first wild Pokemon - {context.get('pokemon', 'a new friend')}! "
                "Gotta catch 'em all! #Pokemon #PokemonRed #LLMLetsPlay"
            ),
            AchievementType.VIRIDIAN_FOREST_BREAK: (
                "Taking a break in Viridian Forest. "
                "It's peaceful here among the trees! #Pokemon #PokemonRed"
            ),
            AchievementType.STARTER_EVOLUTION_1: (
                f"My starter just evolved into {context.get('pokemon', 'its next form')}! "
                "We're getting stronger! #Pokemon #PokemonRed #Evolution"
            ),
            AchievementType.STARTER_EVOLUTION_2: (
                f"FINAL EVOLUTION! My starter is now {context.get('pokemon', 'fully evolved')}! "
                "We're unstoppable! #Pokemon #PokemonRed #Evolution"
            ),
            AchievementType.BADGE_BOULDER: "Earned the Boulder Badge from Brock! 1/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_CASCADE: "Earned the Cascade Badge from Misty! 2/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_THUNDER: "Earned the Thunder Badge from Lt. Surge! 3/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_RAINBOW: "Earned the Rainbow Badge from Erika! 4/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_SOUL: "Earned the Soul Badge from Koga! 5/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_MARSH: "Earned the Marsh Badge from Sabrina! 6/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_VOLCANO: "Earned the Volcano Badge from Blaine! 7/8 badges collected! #Pokemon #PokemonRed #GymBadge",
            AchievementType.BADGE_EARTH: "Earned the Earth Badge from Giovanni! ALL 8 BADGES COLLECTED! #Pokemon #PokemonRed #GymBadge",
            AchievementType.LEGENDARY_ARTICUNO: "Captured the legendary Articuno! The ice bird is mine! #Pokemon #PokemonRed #Legendary",
            AchievementType.LEGENDARY_ZAPDOS: "Captured the legendary Zapdos! Electric power! #Pokemon #PokemonRed #Legendary",
            AchievementType.LEGENDARY_MOLTRES: "Captured the legendary Moltres! The fire bird joins my team! #Pokemon #PokemonRed #Legendary",
            AchievementType.LEGENDARY_MEWTWO: "Captured MEWTWO! The ultimate Pokemon is mine! #Pokemon #PokemonRed #Legendary",
            AchievementType.POKEMON_CHAMPION: (
                "I DID IT! I'M THE POKEMON LEAGUE CHAMPION! "
                "What an incredible journey! #Pokemon #PokemonRed #Champion"
            ),
            # Scripted photo moments
            AchievementType.SS_ANNE_DECK: (
                "Standing at the bow of the SS Anne, watching the ocean sparkle. "
                "What a view! #Pokemon #PokemonRed #SSAnne"
            ),
            AchievementType.POKEMON_TOWER_SPOOKED: (
                "Pokemon Tower is SO creepy! There are ghosts everywhere! "
                "But I have to be brave... #Pokemon #PokemonRed #LavenderTown"
            ),
            AchievementType.GAME_CORNER_SLOTS: (
                "Trying my luck at the Celadon Game Corner! "
                "Maybe I'll win enough coins for a prize! #Pokemon #PokemonRed #GameCorner"
            ),
            AchievementType.FIGHTING_DOJO: (
                "Training at the Fighting Dojo in Saffron City! "
                "Time to get stronger! #Pokemon #PokemonRed #Training"
            ),
            AchievementType.SAFARI_ZONE_EXPLORER: (
                "Exploring the Safari Zone! So many rare Pokemon here! "
                "Gotta catch 'em all! #Pokemon #PokemonRed #SafariZone"
            ),
            AchievementType.TEAM_ROCKET_FIRST: (
                "Just had my first run-in with Team Rocket! "
                "Those villains won't get away with this! #Pokemon #PokemonRed #TeamRocket"
            ),
            # Scenic/Nature moments
            AchievementType.CERULEAN_CAPE: (
                "The ocean view from Cerulean Cape is breathtaking! "
                "Such a peaceful spot near Bill's house. #Pokemon #PokemonRed #CeruleanCape"
            ),
            AchievementType.MT_MOON_EXIT: (
                "Finally out of Mt. Moon! The sunlight feels so good after all that darkness! "
                "#Pokemon #PokemonRed #MtMoon"
            ),
            AchievementType.ROCK_TUNNEL_EXIT: (
                "I made it through Rock Tunnel! That was the darkest cave ever! "
                "So happy to see the sky again! #Pokemon #PokemonRed #RockTunnel"
            ),
            AchievementType.CYCLING_ROAD: (
                "Cruising down Cycling Road! The wind in my hair feels amazing! "
                "#Pokemon #PokemonRed #CyclingRoad"
            ),
            AchievementType.SEAFOAM_ISLANDS: (
                "The ice caves in Seafoam Islands are stunning! "
                "Freezing cold but so beautiful! #Pokemon #PokemonRed #SeafoamIslands"
            ),
            AchievementType.ROUTE_12_FISHING: (
                "Taking a peaceful fishing break on Route 12. "
                "Just waiting for a bite... #Pokemon #PokemonRed #Fishing"
            ),
            # Milestone moments
            AchievementType.PEWTER_GYM_ENTRANCE: (
                "Standing at Pewter Gym - my FIRST gym challenge! "
                "Brock, here I come! #Pokemon #PokemonRed #PewterGym"
            ),
            AchievementType.INDIGO_PLATEAU: (
                "I made it to the Indigo Plateau! The Pokemon League awaits! "
                "This is what my whole journey has been for! #Pokemon #PokemonRed #PokemonLeague"
            ),
            AchievementType.DAYCARE_VISIT: (
                "Found the Pokemon Daycare on Route 5! "
                "What a cozy place for Pokemon! #Pokemon #PokemonRed #Daycare"
            ),
        }

        return fallbacks.get(
            achievement_type,
            "Making progress on my Pokemon adventure! #Pokemon #PokemonRed #LLMLetsPlay",
        )

    def _build_run_context(
        self,
        is_continuing_run: bool,
        run_state: Any = None,
        game_state: dict = None,
        achievement: Achievement = None,
    ) -> Dict[str, Any]:
        """Build run context dict for Discord display."""
        context = {
            "is_continuing": is_continuing_run,
        }

        # Add achievement info
        if achievement:
            context["achievement"] = achievement.achievement_type.value
            context["achievement_context"] = achievement.context

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
            # Team summary
            party = getattr(run_state, "party", None)
            if not party and game_state:
                party = game_state.get("party", [])

            if party and isinstance(party, list):
                team_strs = []
                for p in party[:3]:  # First 3 Pokemon
                    if isinstance(p, dict):
                        name = p.get("nickname") or p.get("species", "???")
                        level = p.get("level", "?")
                        team_strs.append(f"{name} (Lv{level})")
                if team_strs:
                    context["team"] = ", ".join(team_strs)

            # Playtime
            elapsed = getattr(run_state, "elapsed_seconds", 0)
            if elapsed:
                hours = elapsed / 3600
                context["playtime"] = f"{hours:.1f} hours"

        return context

    # Legacy method for backward compatibility
    async def generate_tweet_text(
        self,
        is_continuing_run: bool,
        run_state: Any = None,
        game_state: dict = None,
    ) -> Optional[str]:
        """Generate tweet text using the LLM (legacy method)."""
        stream_achievement = Achievement(
            achievement_type=AchievementType.STREAM_START,
            triggered_at=datetime.now().isoformat(),
            context={"is_continuing": is_continuing_run},
        )
        return await self._generate_achievement_tweet_text(
            stream_achievement, run_state, game_state
        )


def create_tweet_generator(llm_client: Any = None) -> TweetGenerator:
    """Factory function to create a TweetGenerator instance."""
    return TweetGenerator(llm_client=llm_client)
