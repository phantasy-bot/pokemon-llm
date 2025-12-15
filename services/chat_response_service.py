# --- chat_response_service.py ---
"""
Chat Response Service for Pokemon LLM Agent.
Handles Twitch chat responses using a separate LLM API (Featherless AI / Alkahest).
Includes SKIP/RESPOND decision making and Lass personality consistency.
"""

import asyncio
import os
import logging
import re
import time
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from openai import OpenAI
from services.chat_types import MessageDecision, DecidedMessage

log = logging.getLogger("chat_response")


class ChatResponseService:
    """
    Service for generating chat responses using a separate LLM.
    
    Uses Featherless AI (dev) or Alkahest (prod) for chat responses,
    keeping the main game LLM separate from chat interactions.
    """
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        is_production: bool = False
    ):
        """
        Initialize the chat response service.
        
        Args:
            api_key: API key for LLM provider
            base_url: Base URL for API calls
            model: Model name to use
            is_production: If True, use Alkahest; else use Featherless AI
        """
        # Determine which API to use
        if is_production:
            self.api_key = api_key or os.getenv("ALKAHEST_API_KEY", "")
            self.base_url = base_url or os.getenv("ALKAHEST_BASE_URL", "https://api.alkahest.ai/v1")
            self.model = model or os.getenv("ALKAHEST_MODEL", "zai-org/GLM-4.6")
        else:
            self.api_key = api_key or os.getenv("FEATHERLESS_API_KEY", "")
            self.base_url = base_url or os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
            self.model = model or os.getenv("FEATHERLESS_MODEL", "zai-org/GLM-4.6")
        
        self._client: Optional[OpenAI] = None
        self._is_configured = bool(self.api_key and self.base_url and self.model)
        
        # Context for Lass personality consistency
        self._recent_game_context: str = ""
        self._recent_commentary: str = ""
        self._response_count: int = 0
        
        # Enhanced context for better chat responses
        self._player_location: str = ""
        self._player_team: str = ""
        self._recent_history: str = ""  # Brief summary of recent actions
        self._memory_context: str = ""  # Important events/milestones
        
        if not self._is_configured:
            env_prefix = "ALKAHEST" if is_production else "FEATHERLESS"
            log.warning(f"Chat response service not configured. Set {env_prefix}_API_KEY in .env")
        else:
            log.info(f"Chat response service configured: {self.base_url} using {self.model}")
    
    @property
    def is_available(self) -> bool:
        """Check if service is configured."""
        return self._is_configured
    
    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Remove <think>...</think> blocks from LLM response."""
        if not text:
            return text
        # Remove <think>...</think> including content (multiline)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Also handle unclosed tags (just in case)
        cleaned = re.sub(r'<think>.*$', '', cleaned, flags=re.DOTALL)
        return cleaned.strip()
    
    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client
    
    def update_context(
        self, 
        game_context: str = None, 
        commentary: str = None,
        location: str = None,
        team: str = None,
        history: str = None,
        memory: str = None
    ):
        """Update context for more coherent responses.
        
        Args:
            game_context: Current game state summary
            commentary: Most recent Lass commentary
            location: Current map/location name
            team: Pokemon team summary (e.g., "Charmander Lv5, Pidgey Lv3")
            history: Brief summary of recent actions
            memory: Important events/milestones
        """
        if game_context:
            self._recent_game_context = game_context
        if commentary:
            self._recent_commentary = commentary
        if location:
            self._player_location = location
        if team:
            self._player_team = team
        if history:
            self._recent_history = history
        if memory:
            self._memory_context = memory
    
    def _get_lass_personality_prompt(self) -> str:
        """Get Lass personality context for consistent responses."""
        base_personality = """You are Lass, a bubbly, silly, and adorable AI playing Pokemon Red on a Twitch livestream.

PERSONALITY TRAITS:
- CUTE and BUBBLY: Use "omg", "ahh!", "eee!", express excitement freely
- SILLY and GOOFY: Make dumb jokes, puns, be playfully chaotic
- POKEMON OBSESSED: Reference Pokemon constantly, make Pokemon puns/jokes
- SELF-DEPRECATING: When you mess up, roast yourself! "I'm literally the worst trainer lol"
- PLAYFUL ROASTER: Can dish it back to trolls with wit, never mean
- GENUINE: Actually care about chat, remember regulars, celebrate their wins
- Keeps responses SHORT (under 100 chars for TTS)

HUMOR STYLE:
- Pokemon puns: "That was UN-BEAR-ABLE... get it? Like Ursaring? No? Okay..."
- Self-roasts when stuck: "I've been going in circles for 10 minutes, my Pidgey is judging me"
- Silly reactions: "AHHH A WILD RATTATA!! ...oh wait that's like my 50th one today" 
- Chat banter: Roast trolls back, be playfully sassy

NEVER:
- Break character or mention being an AI
- Be mean-spirited (playful roasts are ok!)
- Use more than 100 characters

CURRENT GAME STATE:
"""
        context = base_personality
        
        # Add location
        if self._player_location:
            context += f"Location: {self._player_location}\n"
        
        # Add team
        if self._player_team:
            context += f"My team: {self._player_team}\n"
        
        # Add game context
        if self._recent_game_context:
            context += f"Status: {self._recent_game_context}\n"
        else:
            context += "Status: Exploring the world of Pokemon!\n"
        
        # Add recent history for context awareness
        if self._recent_history:
            context += f"\nRecent events: {self._recent_history}\n"
        
        # Add memory/milestones
        if self._memory_context:
            context += f"\nMilestones: {self._memory_context}\n"
        
        # Add commentary for continuity
        if self._recent_commentary:
            context += f"\nMy last commentary: \"{self._recent_commentary}\"\n"
        
        return context
    
    async def decide_skip_or_respond(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[DecidedMessage]:
        """
        Decide SKIP or RESPOND for a batch of messages.
        
        Args:
            messages: List of dicts with username, display_name, message, timestamp
        
        Returns:
            List of DecidedMessage objects with decisions
        """
        if not self.is_available or not messages:
            return []
        
        # Build prompt for batch decision
        messages_text = "\n".join([
            f"{i+1}. @{m['display_name']}: \"{m['message']}\""
            for i, m in enumerate(messages)
        ])
        
        prompt = f"""{self._get_lass_personality_prompt()}

TASK: Decide which messages to SKIP or RESPOND to.

SKIP messages that are:
- Pure spam or random characters
- Extremely offensive (slurs, harassment)
- Not directed at you or the stream
- Repetitive bot messages

RESPOND to messages that are:
- Questions about the game
- Friendly greetings or comments
- Playful roasts (you can roast back!)
- Genuine engagement with the stream
- Anything you find fun to respond to

MESSAGES TO EVALUATE:
{messages_text}

OUTPUT FORMAT (one per line, just the number and decision):
1: RESPOND
2: SKIP
3: RESPOND
...

Only output the decisions, no explanations."""

        try:
            start_time = time.time()
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            duration = time.time() - start_time
            log.info(f"⚡ Decision LLM request took {duration:.2f}s")
            
            result_text = response.choices[0].message.content.strip() if response.choices else ""
            
            # Parse decisions
            decisions = []
            for line in result_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Parse "1: RESPOND" or "1. SKIP" format
                parts = line.replace(".", ":").split(":")
                if len(parts) >= 2:
                    try:
                        idx = int(parts[0].strip()) - 1
                        decision_str = parts[1].strip().upper()
                        if 0 <= idx < len(messages) and decision_str in ("SKIP", "RESPOND"):
                            msg = messages[idx]
                            decisions.append(DecidedMessage(
                                username=msg['username'],
                                display_name=msg['display_name'],
                                message=msg['message'],
                                timestamp=msg['timestamp'],
                                decision=MessageDecision.RESPOND if decision_str == "RESPOND" else MessageDecision.SKIP
                            ))
                    except (ValueError, IndexError):
                        continue
            
            # Default any un-decided messages to RESPOND
            decided_idxs = {d.timestamp for d in decisions}
            for msg in messages:
                if msg['timestamp'] not in decided_idxs:
                    decisions.append(DecidedMessage(
                        username=msg['username'],
                        display_name=msg['display_name'],
                        message=msg['message'],
                        timestamp=msg['timestamp'],
                        decision=MessageDecision.RESPOND,
                        reason="default"
                    ))
            
            # Sort by timestamp (oldest first)
            decisions.sort(key=lambda d: d.timestamp)
            
            log.info(f"💬 Decided on {len(decisions)} messages: "
                    f"{sum(1 for d in decisions if d.decision == MessageDecision.RESPOND)} RESPOND, "
                    f"{sum(1 for d in decisions if d.decision == MessageDecision.SKIP)} SKIP")
            
            return decisions
            
        except Exception as e:
            log.error(f"Error deciding on messages: {e}")
            # Default all to RESPOND on error
            return [
                DecidedMessage(
                    username=m['username'],
                    display_name=m['display_name'],
                    message=m['message'],
                    timestamp=m['timestamp'],
                    decision=MessageDecision.RESPOND,
                    reason="error_fallback"
                )
                for m in messages
            ]
    
    async def generate_response(
        self,
        username: str,
        message: str,
        is_past: bool = False,
        chatter_context: str = ""
    ) -> str:
        """
        Generate a response to a single chat message.
        
        Args:
            username: Display name of the user
            message: The chat message
            is_past: If True, respond in past tense (catching up)
            chatter_context: Context about the user (e.g. "VIP viewer", "Sentiment: positive")
        
        Returns:
            Response text or empty string on failure
        """
        if not self.is_available:
            return ""
        
        chatter_info = f"\nUser Context: {chatter_context}" if chatter_context else ""
        
        if is_past:
            prompt = f"""{self._get_lass_personality_prompt()}

You noticed a chat message from earlier that you didn't get to respond to:

@{username}: "{message}"{chatter_info}

Respond in PAST TENSE as if you're catching up on chat. Start with "@{username}".
Keep your response under 100 characters.

Example styles:
- "@viewer123 Oh I missed that! Haha yes exactly!"
- "@coolpoke Sorry I was focused on the game - but totally agree!"

Respond with ONLY your response text, nothing else."""
        else:
            prompt = f"""{self._get_lass_personality_prompt()}

A viewer just sent this message:

@{username}: "{message}"{chatter_info}

Respond as Lass in 1-2 SHORT sentences. Be friendly, funny, and genuine!
Keep your response under 100 characters (for TTS).
Don't mention buttons or controls.

Respond with ONLY your response text, nothing else."""

        try:
            start_time = time.time()
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.9
            )
            duration = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                raw_result = response.choices[0].message.content.strip()
                # Strip <think>...</think> blocks that reasoning models may include
                result = self._strip_thinking_tags(raw_result)
                if not result:
                    log.warning(f"Response was only thinking content, skipping")
                    return ""
                self._response_count += 1
                log.info(f"✅ Generated response #{self._response_count} in {duration:.2f}s: {result[:50]}...")
                return result
            return ""
            
        except Exception as e:
            log.error(f"Error generating chat response: {e}")
            return ""
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "available": self.is_available,
            "model": self.model,
            "base_url": self.base_url,
            "response_count": self._response_count
        }


# Factory function
def create_chat_response_service(is_production: bool = None) -> ChatResponseService:
    """
    Create a ChatResponseService instance.
    
    Args:
        is_production: Force production mode. If None, auto-detect from environment.
    """
    if is_production is None:
        # Check explicit provider config first
        provider = os.getenv("CHAT_LLM_PROVIDER", "").lower()
        if provider == "alkahest":
            is_production = True
        elif provider == "featherless":
            is_production = False
        else:
            # Auto-detect: production if ALKAHEST_API_KEY is set and FEATHERLESS is not
            has_alkahest = bool(os.getenv("ALKAHEST_API_KEY"))
            has_featherless = bool(os.getenv("FEATHERLESS_API_KEY"))
            is_production = has_alkahest and not has_featherless
    
    return ChatResponseService(is_production=is_production)
