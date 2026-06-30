import unittest

from backend.utils.chat import get_command_reply


class ChatCommandTests(unittest.TestCase):
    def test_waifu_command_returns_reply(self):
        reply = get_command_reply("/waifu")
        self.assertIsNotNone(reply)
        self.assertIn("waifu", reply.lower())

    def test_unknown_command_returns_none(self):
        self.assertIsNone(get_command_reply("/unknown"))


if __name__ == "__main__":
    unittest.main()
