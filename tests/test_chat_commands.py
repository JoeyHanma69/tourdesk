import subprocess
import sys
import unittest
from pathlib import Path

from backend.utils.chat import get_command_reply


REPO_ROOT = Path(__file__).resolve().parents[1]


class ChatCommandTests(unittest.TestCase):
    def test_waifu_command_returns_reply(self):
        reply = get_command_reply("/waifu")
        self.assertIsNotNone(reply)
        self.assertIn("waifu", reply.lower())

    def test_unknown_command_returns_none(self):
        self.assertIsNone(get_command_reply("/unknown"))

    def test_app_entrypoint_starts_without_import_error(self):
        try:
            subprocess.run(
                [sys.executable, str(REPO_ROOT / "backend" / "app.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired as exc:
            combined_output = (exc.stdout or "") + (exc.stderr or "")
            self.assertNotIn("ModuleNotFoundError", combined_output)
        except subprocess.CalledProcessError as exc:
            combined_output = (exc.stdout or "") + (exc.stderr or "")
            self.assertNotIn("ModuleNotFoundError", combined_output)
        else:
            self.fail("App entrypoint exited before the server stayed running")


if __name__ == "__main__":
    unittest.main()
