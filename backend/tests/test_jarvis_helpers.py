from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from jarvis_modules.browser_matching import best_text_match, score_text_match
from jarvis_modules.disk_audit import build_disk_cleanup_report, format_bytes
from jarvis_modules.elevenlabs_tts import DEFAULT_VOICE_ID, ElevenLabsTTSError, api_key_from_config, synthesize_speech
from jarvis_modules.self_knowledge import build_self_knowledge, compact_self_knowledge_text
from jarvis_modules.self_improvement import save_self_improvement_request, safety_review


class BrowserMatchingTests(unittest.TestCase):
    def test_semantic_learn_more_match(self):
        candidates = [
            {"index": 0, "text": "Accept"},
            {"index": 1, "text": "Learn more"},
            {"index": 2, "text": "Contact"},
        ]
        match = best_text_match("More information", candidates)
        self.assertIsNotNone(match)
        self.assertEqual(match["index"], 1)

    def test_exact_text_scores_higher_than_unrelated(self):
        self.assertGreater(score_text_match("System report", "System report"), score_text_match("System report", "Weather"))


class DiskAuditTests(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")

    def test_build_disk_cleanup_report_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            downloads = root / "Downloads"
            downloads.mkdir()
            target = downloads / "large.tmp"
            target.write_bytes(b"x" * 2048)

            report = build_disk_cleanup_report(root)

            self.assertIn("Cleanup candidates", report)
            self.assertIn("large.tmp", report)
            self.assertTrue(target.exists())


class ElevenLabsConfigTests(unittest.TestCase):
    def test_default_voice_id_matches_requested_voice(self):
        self.assertEqual(DEFAULT_VOICE_ID, "HH8sIQq8WOcER3Nu118i")

    def test_missing_key_fails_before_network(self):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": ""}, clear=False):
            self.assertEqual(api_key_from_config({}), "")
            with self.assertRaises(ElevenLabsTTSError):
                synthesize_speech("hello", {"elevenlabs_api_key": ""})


class SelfKnowledgeTests(unittest.TestCase):
    def test_build_self_knowledge_skips_secret_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assistant.py").write_text(
                '"""Tiny assistant."""\n\nclass TinyAssistant:\n    pass\n',
                encoding="utf-8",
            )
            (root / ".env").write_text("API_KEY=secret", encoding="utf-8")
            output = root / "self.json"

            data = build_self_knowledge(root, output)

            paths = {entry["path"] for entry in data["entries"]}
            self.assertIn("assistant.py", paths)
            self.assertNotIn(".env", paths)
            self.assertGreaterEqual(data["skipped"]["sensitive_files"], 1)
            self.assertTrue(output.exists())

    def test_compact_self_knowledge_includes_code_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "core.py").write_text(
                "class Core:\n    pass\n\ndef boot():\n    return True\n",
                encoding="utf-8",
            )
            output = root / "self.json"
            build_self_knowledge(root, output)

            text = compact_self_knowledge_text(output)

            self.assertIn("Core", text)
            self.assertIn("core.py", text)


class SelfImprovementTests(unittest.TestCase):
    def test_safe_self_improvement_request_is_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "requests.json"

            request = save_self_improvement_request(target, "add a feature to jarvis that summarizes my notes")

            self.assertTrue(request["allowed"])
            self.assertEqual(request["status"], "queued_for_implementation")
            self.assertTrue(target.exists())

    def test_always_on_camera_request_is_blocked(self):
        allowed, category, note = safety_review(
            "edit yourself to always keep camera on and analyse me whole time and all activities"
        )

        self.assertFalse(allowed)
        self.assertEqual(category, "covert_surveillance")
        self.assertIn("blocked", note.lower())


if __name__ == "__main__":
    unittest.main()
