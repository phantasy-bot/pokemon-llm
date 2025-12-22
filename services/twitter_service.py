"""
Twitter/X API Service for Pokemon LLM Agent.

Handles posting tweets with images using the X API v2.
Uses OAuth 1.0a User Context for posting (Free tier: 500 posts/month).
"""

import os
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("twitter_service")

# Tweet tracking file for rate limit awareness
TWEET_HISTORY_FILE = "data/tweet_history.json"


@dataclass
class TweetResult:
    """Result of a tweet post attempt."""

    success: bool
    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TwitterService:
    """
    X/Twitter API client for posting tweets with media.

    Uses tweepy for OAuth 1.0a authentication and API v2 endpoints.
    Tracks tweet history for rate limit awareness.
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
    ):
        """
        Initialize the Twitter service.

        Args:
            api_key: X API Key (Consumer Key)
            api_secret: X API Secret (Consumer Secret)
            access_token: OAuth 1.0a Access Token
            access_token_secret: OAuth 1.0a Access Token Secret
        """
        self.api_key = api_key or os.getenv("TWITTER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET", "")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_token_secret = access_token_secret or os.getenv(
            "TWITTER_ACCESS_TOKEN_SECRET", ""
        )

        self.enabled = os.getenv("TWITTER_ENABLED", "false").lower() == "true"
        self._client = None
        self._api_v1 = None  # For media upload (v1.1 endpoint)

        # Monthly limit tracking (Free tier: 500 posts/month)
        self.monthly_limit = 500
        self._tweet_history = self._load_tweet_history()

        if self.enabled:
            if self._validate_credentials():
                log.info("Twitter Service initialized and enabled")
            else:
                log.warning("Twitter enabled but credentials incomplete")
                self.enabled = False
        else:
            log.info("Twitter Service disabled")

    def _validate_credentials(self) -> bool:
        """Check if all required credentials are present."""
        return all(
            [
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret,
            ]
        )

    def _init_client(self):
        """Initialize the tweepy client (lazy initialization)."""
        if self._client is not None:
            return

        try:
            import tweepy

            # Client for API v2 (tweets)
            self._client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )

            # API v1.1 for media upload
            auth = tweepy.OAuth1UserHandler(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret,
            )
            self._api_v1 = tweepy.API(auth)

            log.info("Tweepy client initialized successfully")
        except ImportError:
            log.error("tweepy not installed. Run: pip install tweepy")
            self.enabled = False
        except Exception as e:
            log.error(f"Failed to initialize tweepy client: {e}")
            self.enabled = False

    def _load_tweet_history(self) -> list:
        """Load tweet history from file."""
        try:
            if os.path.exists(TWEET_HISTORY_FILE):
                with open(TWEET_HISTORY_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            log.warning(f"Failed to load tweet history: {e}")
        return []

    def _save_tweet_history(self):
        """Save tweet history to file."""
        try:
            Path(TWEET_HISTORY_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(TWEET_HISTORY_FILE, "w") as f:
                json.dump(self._tweet_history, f, indent=2)
        except Exception as e:
            log.warning(f"Failed to save tweet history: {e}")

    def get_monthly_tweet_count(self) -> int:
        """Get the number of tweets posted this month."""
        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        count = 0
        for tweet in self._tweet_history:
            try:
                tweet_time = datetime.fromisoformat(tweet.get("timestamp", ""))
                if tweet_time.strftime("%Y-%m") == current_month:
                    count += 1
            except (ValueError, TypeError):
                continue

        return count

    def get_remaining_tweets(self) -> int:
        """Get remaining tweets available this month."""
        return max(0, self.monthly_limit - self.get_monthly_tweet_count())

    async def upload_media(self, image_path: str) -> Optional[str]:
        """
        Upload an image to Twitter and return the media ID.

        Args:
            image_path: Path to the image file

        Returns:
            Media ID string, or None on failure
        """
        if not self.enabled:
            log.warning("Twitter service is disabled")
            return None

        if not os.path.exists(image_path):
            log.error(f"Image file not found: {image_path}")
            return None

        self._init_client()
        if self._api_v1 is None:
            return None

        try:
            # Check file size (X limit is 5MB for images)
            file_size = os.path.getsize(image_path)
            if file_size > 5 * 1024 * 1024:
                log.warning(f"Image too large ({file_size} bytes), may need resizing")

            # Upload using v1.1 media endpoint
            media = self._api_v1.media_upload(filename=image_path)
            media_id = str(media.media_id)

            log.info(f"Uploaded media: {media_id}")
            return media_id

        except Exception as e:
            log.error(f"Media upload failed: {e}")
            return None

    async def post_tweet(
        self,
        text: str,
        image_path: str = None,
        image_paths: list = None,
    ) -> TweetResult:
        """
        Post a tweet, optionally with one or more images.

        Args:
            text: Tweet text (max 280 characters)
            image_path: Optional path to single image file (legacy)
            image_paths: Optional list of image paths (up to 4 images)

        Returns:
            TweetResult with success status and tweet details
        """
        if not self.enabled:
            return TweetResult(success=False, error="Twitter service is disabled")

        # Check rate limit
        remaining = self.get_remaining_tweets()
        if remaining <= 0:
            return TweetResult(
                success=False,
                error=f"Monthly tweet limit reached ({self.monthly_limit})",
            )

        # Validate text length
        if len(text) > 280:
            log.warning(f"Tweet text too long ({len(text)} chars), truncating")
            text = text[:277] + "..."

        self._init_client()
        if self._client is None:
            return TweetResult(
                success=False, error="Failed to initialize Twitter client"
            )

        try:
            media_ids = []

            # Build list of images to upload
            images_to_upload = []
            if image_paths:
                images_to_upload = image_paths[:4]  # Twitter limit: max 4 images
            elif image_path:
                images_to_upload = [image_path]

            # Upload all images
            for img_path in images_to_upload:
                if img_path and os.path.exists(img_path):
                    media_id = await self.upload_media(img_path)
                    if media_id:
                        media_ids.append(media_id)
                    else:
                        log.warning(f"Failed to upload media: {img_path}")

            if not media_ids:
                media_ids = None

            log.info(f"Posting tweet with {len(media_ids) if media_ids else 0} images")

            # Post the tweet
            response = self._client.create_tweet(
                text=text,
                media_ids=media_ids,
            )

            tweet_id = response.data.get("id") if response.data else None
            tweet_url = f"https://x.com/i/status/{tweet_id}" if tweet_id else None

            # Record in history
            self._tweet_history.append(
                {
                    "tweet_id": tweet_id,
                    "text": text[:100],  # Store truncated text
                    "has_media": len(images_to_upload) > 0,
                    "media_count": len(media_ids) if media_ids else 0,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._save_tweet_history()

            log.info(f"Tweet posted successfully: {tweet_url}")

            return TweetResult(
                success=True,
                tweet_id=tweet_id,
                tweet_url=tweet_url,
            )

        except Exception as e:
            error_msg = str(e)
            log.error(f"Failed to post tweet: {error_msg}")

            # Check for specific error types
            if "duplicate" in error_msg.lower():
                error_msg = "Duplicate tweet content"
            elif "rate" in error_msg.lower():
                error_msg = "Rate limit exceeded"

            return TweetResult(
                success=False,
                error=error_msg,
            )


def create_twitter_service() -> TwitterService:
    """Factory function to create a Twitter service instance."""
    return TwitterService()
