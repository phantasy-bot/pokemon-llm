"""
Zora Poster Service.

Orchestrates the creation of Zora posts (coins) for achievements.
- Polls ZoraAchievementTracker for pending achievements
- Generates images (ComfyUI) or retrieves screenshots
- Creates collages for gallery posts
- Calls Chronicle Server (Zora Sidecar) to create DRAFTS
- Handles rate limiting and queues
- Supports token-gated exclusive content
"""

import asyncio
import logging
import os
import time
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

# Integration imports
from trackers.zora_achievement_tracker import (
    get_zora_achievement_tracker,
    ZoraAchievement,
    ZoraAchievementTier,
    ZoraAchievementType,
)
from services.screenshot_manager import get_screenshot_manager
from trackers.achievement_tracker import create_achievement_tracker, AchievementType

log = logging.getLogger("zora_poster")

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    log.warning("httpx not installed. Zora posting disabled.")

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    log.warning("Pillow not installed. Image processing/collages disabled.")


# Configuration
ZORA_SIDECAR_URL = os.getenv("ZORA_SIDECAR_URL", "http://localhost:3001")
ZORA_POSTING_ENABLED = os.getenv("ZORA_POSTING_ENABLED", "true").lower() == "true"
ZORA_GATING_ENABLED = os.getenv("ZORA_GATING_ENABLED", "false").lower() == "true"
MIN_POST_INTERVAL = int(os.getenv("ZORA_MIN_POST_INTERVAL", "300"))


class ZoraPosterService:
    """
    Orchestrates Zora posting workflow.
    """

    def __init__(self):
        self.tracker = get_zora_achievement_tracker()
        self.screenshot_manager = get_screenshot_manager()
        self.sidecar_url = ZORA_SIDECAR_URL

        self._running = False
        self._last_post_time = 0
        self._worker_task: Optional[asyncio.Task] = None
        self._client: Optional[httpx.AsyncClient] = None

        # State for ComfyUI generation (if needed)
        self.comfyui_service = None  # To be injected or imported

        if not ZORA_POSTING_ENABLED:
            log.info("Zora posting is disabled in config")

    async def start(self):
        """Start the posting worker loop."""
        if not ZORA_POSTING_ENABLED or not HTTPX_AVAILABLE:
            return

        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        log.info("Zora poster service started")

    async def stop(self):
        """Stop the posting worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=120.0
            )  # Long timeout for upload/mint
        return self._client

    async def _worker_loop(self):
        """Main loop checking for pending posts."""
        while self._running:
            try:
                # 1. Check rate limit
                time_since_last = time.time() - self._last_post_time
                if time_since_last < MIN_POST_INTERVAL:
                    await asyncio.sleep(10)
                    continue

                # 2. Check pending achievement
                achievement = self.tracker.get_pending_achievement()
                if not achievement:
                    await asyncio.sleep(5)
                    continue

                log.info(f"Processing Zora achievement: {achievement.get_title()}")

                # 3. Prepare content (Image & Metadata)
                post_data = await self._prepare_post(achievement)

                if not post_data:
                    log.error(
                        "Failed to prepare post data. Skipping/Clearing achievement."
                    )
                    self.tracker.clear_pending_achievement()
                    continue

                # 4. Send to Chronicle Server (Sidecar) as DRAFT
                success = await self._send_to_sidecar(post_data)

                if success:
                    # 5. Mark complete
                    self.tracker.mark_posted(
                        key=achievement.achievement_type.value,
                        coin_address=post_data.get("coinAddress", "draft-id"),
                    )

                    # Update tracker with coin address and status by iterating keys
                    key = None
                    for k, v in self.tracker.triggered.items():
                        if v == achievement:
                            key = k
                            break
                    if key:
                        self.tracker.mark_posted(
                            key, post_data.get("coinAddress", "draft-id")
                        )

                    self.tracker.clear_pending_achievement()
                    self._last_post_time = time.time()
                    log.info(
                        f"✅ Successfully sent draft to Chronicle: {achievement.get_title()}"
                    )
                else:
                    log.error("Failed to send draft to Chronicle. Will retry later.")
                    await asyncio.sleep(60)  # Backoff

            except Exception as e:
                log.error(f"Error in Zora poster loop: {e}")
                await asyncio.sleep(30)

    async def _prepare_post(
        self, achievement: ZoraAchievement
    ) -> Optional[Dict[str, Any]]:
        """Prepare image and metadata for the post."""

        # Determine image path
        image_path = None
        exclusive_path = None

        if achievement.tier == ZoraAchievementTier.MAJOR:
            # Major: Try to generate AI image or use screenshot
            image_path = self.screenshot_manager.get_latest_path()

            # If gating enabled, we could use the raw screenshot or save file as exclusive content
            # For now, let's just use the screenshot as exclusive too for testing the pipeline
            if ZORA_GATING_ENABLED:
                exclusive_path = image_path

        elif achievement.tier == ZoraAchievementTier.PROGRESS:
            # Progress: Create gallery collage
            image_path = self._create_collage()

        else:  # MINOR
            # Minor: Latest screenshot
            image_path = self.screenshot_manager.get_latest_path()

        if not image_path or not os.path.exists(image_path):
            log.warning("No image available for Zora post")
            return None

        # Prepare metadata
        title = achievement.get_title()
        description = self._generate_description(achievement)

        attributes = [
            {"trait_type": "Tier", "value": achievement.tier.value},
            {"trait_type": "Type", "value": achievement.achievement_type.value},
            {"trait_type": "Post Number", "value": achievement.post_number},
        ]

        # Add context attributes
        for k, v in achievement.context.items():
            if isinstance(v, (str, int, float, bool)):
                attributes.append(
                    {"trait_type": k.replace("_", " ").title(), "value": v}
                )

        return {
            "name": title,
            "symbol": f"LLP-{achievement.post_number:03d}",
            "description": description,
            "image_path": image_path,
            "exclusive_path": exclusive_path,
            "attributes": attributes,
            "status": "draft",  # FORCE DRAFT
        }

    def _generate_description(self, achievement: ZoraAchievement) -> str:
        """Generate description text."""
        lines = [
            f"🎮 LassPlaysPokemon - Post #{achievement.post_number}",
            f"Achievement: {achievement.get_title()}",
            f"Time: {achievement.triggered_at}",
            "",
        ]

        # Context details
        for k, v in achievement.context.items():
            lines.append(f"• {k.replace('_', ' ').title()}: {v}")

        lines.append("")

        if achievement.should_include_footer():
            lines.append("Watch live: twitch.tv/lassplayspokemon")
            lines.append("Token:  on pump.fun")
            if ZORA_GATING_ENABLED:
                lines.append("🔒 Exclusive content available for holders.")

        return "\n".join(lines)

    def _create_collage(self) -> Optional[str]:
        """Create a collage from recent screenshots."""
        if not PIL_AVAILABLE:
            return self.screenshot_manager.get_latest_path()

        paths = self.screenshot_manager.get_gallery_paths(count=6)
        if not paths:
            return None

        try:
            images = [Image.open(p) for p in paths]
            if not images:
                return None

            # Create a 2x3 or 3x2 grid depending on count
            width, height = images[0].size
            cols = 2
            rows = (len(images) + 1) // 2

            collage = Image.new("RGB", (width * cols, height * rows))

            for i, img in enumerate(images):
                x = (i % cols) * width
                y = (i // cols) * height
                collage.paste(img, (x, y))

            # Save collage
            output_path = os.path.join(
                self.screenshot_manager.gallery_dir, f"collage_{int(time.time())}.png"
            )
            collage.save(output_path)
            return output_path

        except Exception as e:
            log.error(f"Failed to create collage: {e}")
            return self.screenshot_manager.get_latest_path()

    async def _send_to_sidecar(self, post_data: Dict) -> bool:
        """Send post data to Chronicle Server."""
        client = await self._get_client()

        try:
            # Get API Key from environment
            api_key = os.getenv("CHRONICLE_SECRET_KEY")
            if not api_key:
                log.error(
                    "CHRONICLE_SECRET_KEY not set. Cannot authenticate with Chronicle."
                )
                return False

            # Prepare files list for multipart upload
            files_list = []

            # Public Image
            img_f = open(post_data["image_path"], "rb")
            files_list.append(("image", ("image.png", img_f, "image/png")))

            # Exclusive Content (Optional)
            ex_f = None
            if post_data.get("exclusive_path"):
                ex_f = open(post_data["exclusive_path"], "rb")
                files_list.append(
                    ("exclusive", ("content.dat", ex_f, "application/octet-stream"))
                )

            data = {
                "name": post_data["name"],
                "symbol": post_data["symbol"],
                "description": post_data["description"],
                "attributes": json.dumps(post_data["attributes"]),
                "status": post_data.get(
                    "status", "draft"
                ),  # Default to draft if not specified
            }

            try:
                # Add retry logic for sidecar connection
                response = None
                max_retries = 3

                if not HTTPX_AVAILABLE:
                    log.error("httpx not available, cannot post to sidecar")
                    return False

                for attempt in range(max_retries):
                    try:
                        response = await client.post(
                            f"{self.sidecar_url}/api/drop",
                            data=data,
                            files=files_list,
                            timeout=120.0,
                            headers={"x-api-key": api_key},  # Auth Header
                        )
                        break  # Success
                    except Exception as e:
                        # Catch generic exception if httpx types aren't available to reference directly
                        if attempt == max_retries - 1:
                            raise  # Re-raise on final failure
                        log.warning(
                            f"Sidecar connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying..."
                        )
                        await asyncio.sleep(2 * (attempt + 1))  # Backoff

                if response and response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        post_data["coinAddress"] = result.get(
                            "coinAddress"
                        ) or result.get("id")
                        return True
                    else:
                        log.error(f"Sidecar error: {result.get('error')}")
                else:
                    log.error(
                        f"Sidecar HTTP error: {response.status_code if response else 'None'} {response.text if response else 'None'}"
                    )
            finally:
                img_f.close()
                if ex_f:
                    ex_f.close()

        except Exception as e:
            log.error(f"Failed to call sidecar: {e}")

        return False


# Singleton
_zora_poster: Optional[ZoraPosterService] = None


def get_zora_poster_service() -> ZoraPosterService:
    global _zora_poster
    if _zora_poster is None:
        _zora_poster = ZoraPosterService()
    return _zora_poster
