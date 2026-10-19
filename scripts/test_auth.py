"""Offline tests for episode environment selector compatibility."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import auth


class EpisodeEnvironmentTests(unittest.TestCase):
    def test_episode_twelve_selectors_resolve_renamed_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / "episodes" / "ep-12-business-apps-work-iq" / ".env"
            env_file.parent.mkdir(parents=True)
            env_file.touch()
            with patch.object(auth, "REPO_ROOT", root):
                for selector in (
                    "ep-12-business-apps-work-iq",
                    "ep-12-copilot-chat-agent-builder",
                    "ep-12-dataverse-webiq",
                ):
                    with self.subTest(selector=selector):
                        self.assertEqual(auth._resolve_env_file(selector), env_file)


if __name__ == "__main__":
    unittest.main()
