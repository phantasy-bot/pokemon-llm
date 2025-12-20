import unittest
import os
import json
import shutil
from unittest.mock import MagicMock, AsyncMock

# Set feature flags for testing
os.environ["TWITCH_ENABLE_CHAT_MEMORY"] = "true"
os.environ["TWITCH_ENABLE_PREDICTIONS"] = "true"

from services.twitch_engagement_service import TwitchEngagementService, TwitchChatterMemory, ChatterProfile
from services.chat_types import ChatMessage

class TestTwitchEngagement(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for memory
        self.test_memory_file = "tests/data/test_twitch_chatters.json"
        os.makedirs("tests/data", exist_ok=True)
        if os.path.exists(self.test_memory_file):
            os.remove(self.test_memory_file)
            
        self.mock_twitch_service = MagicMock()
        self.mock_twitch_service._bot = AsyncMock()
        self.engagement = TwitchEngagementService(self.mock_twitch_service)
        self.engagement.memory.filepath = self.test_memory_file
        # Reload memory with new path
        self.engagement.memory.chatters = {}

    def tearDown(self):
        if os.path.exists("tests/data"):
            shutil.rmtree("tests/data")

    def test_memory_update_and_persistence(self):
        msg = ChatMessage(
            username="testuser",
            display_name="TestUser",
            message="I love this stream!",
            timestamp=1234567890,
            is_subscriber=False
        )
        
        # 1. Update memory
        self.engagement.on_message(msg)
        
        # Verify stats
        chatter = self.engagement.memory.chatters["testuser"]
        self.assertEqual(chatter.interaction_count, 1)
        self.assertGreater(chatter.sentiment_score, 0) # "love" should be positive
        
        # 2. Check persistence
        self.assertTrue(os.path.exists(self.test_memory_file))
        with open(self.test_memory_file, 'r') as f:
            data = json.load(f)
            self.assertIn("testuser", data)
            self.assertEqual(data["testuser"]["interaction_count"], 1)

    def test_relationship_tier_progression(self):
        msg = ChatMessage("user2", "User2", "hi", 0, False)
        
        # Simulate 21 messages
        for _ in range(21):
            self.engagement.on_message(msg)
            
        chatter = self.engagement.memory.chatters["user2"]
        self.assertEqual(chatter.relationship_tier, "Regular")

    def test_context_generation(self):
        msg = ChatMessage("user3", "User3", "You suck", 0, False)
        for _ in range(10):
            self.engagement.on_message(msg)
        
        context = self.engagement.memory.get_context("user3")
        self.assertIn("New viewer", context)
        self.assertIn("Sentiment: negative", context) # "suck" is negative

if __name__ == '__main__':
    unittest.main()
