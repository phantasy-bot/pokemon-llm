import unittest
from core.llmdriver import compress_chat_history

class TestCompression(unittest.TestCase):
    def test_compress_simple(self):
        history = [
            {"role": "user", "content": "state1"},
            {"role": "assistant", "content": "Action: U;"}
        ]
        # Should compress
        result = compress_chat_history(history, "Action: U;")
        self.assertTrue(result)
        self.assertEqual(history[-1]["content"], "Action: U; (x2)")

    def test_compress_increment(self):
        history = [
            {"role": "user", "content": "state1"},
            {"role": "assistant", "content": "Action: U; (x2)"}
        ]
        # Should increment to x3
        result = compress_chat_history(history, "Action: U;")
        self.assertTrue(result)
        self.assertEqual(history[-1]["content"], "Action: U; (x3)")

    def test_no_compress_different(self):
        history = [
            {"role": "user", "content": "state1"},
            {"role": "assistant", "content": "Action: U;"}
        ]
        # Different action
        result = compress_chat_history(history, "Action: D;")
        self.assertFalse(result)
        self.assertEqual(history[-1]["content"], "Action: U;")

    def test_no_compress_long(self):
        history = [
            {"role": "user", "content": "state1"},
            {"role": "assistant", "content": "A" * 200}
        ]
        # Too long content
        result = compress_chat_history(history, "A" * 200)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
