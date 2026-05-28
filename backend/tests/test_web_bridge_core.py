from __future__ import annotations

import enum
import json
import unittest
from collections import namedtuple

import jarvis_web
import backend.main as backend_main


class ExampleEnum(enum.Enum):
    READY = "ready"


class WebBridgeCoreTests(unittest.TestCase):
    def test_make_json_safe_handles_namedtuple_and_enum(self):
        Point = namedtuple("Point", ["x", "state"])
        safe = jarvis_web._make_json_safe({"point": Point(2, ExampleEnum.READY)})
        self.assertEqual(safe, {"point": {"x": 2, "state": "ready"}})

    def test_json_bytes_is_ascii_json(self):
        status, body = jarvis_web._json_bytes({"ok": True, "text": "JARVIS"}, status=202)
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body.decode("utf-8")), {"ok": True, "text": "JARVIS"})

    def test_action_json_detection(self):
        self.assertTrue(jarvis_web._looks_like_action_json('{"action":"click","x":10,"y":20}'))
        self.assertFalse(jarvis_web._looks_like_action_json('{"action":"answer","text":"hello"}'))
        self.assertFalse(jarvis_web._looks_like_action_json("normal answer"))

    def test_secret_placeholder_is_not_reported_as_configured(self):
        self.assertFalse(jarvis_web._has_secret("YOUR_API_KEY"))
        self.assertTrue(jarvis_web._has_secret("real-looking-secret"))

    def test_web_tokens_must_be_strong(self):
        self.assertFalse(jarvis_web._token_is_strong(""))
        self.assertFalse(jarvis_web._token_is_strong("jarvis"))
        self.assertFalse(jarvis_web._token_is_strong("1234"))
        self.assertTrue(jarvis_web._token_is_strong("a" * jarvis_web.MIN_WEB_TOKEN_LENGTH))

    def test_secure_token_equal_rejects_legacy_bypasses(self):
        expected = "x" * jarvis_web.MIN_WEB_TOKEN_LENGTH
        self.assertTrue(jarvis_web._secure_token_equal(expected, expected))
        self.assertFalse(jarvis_web._secure_token_equal(expected, "jarvis"))
        self.assertFalse(jarvis_web._secure_token_equal(expected, "1234"))
        self.assertFalse(jarvis_web._secure_token_equal("jarvis", "jarvis"))

    def test_origin_policy_only_allows_same_local_origin(self):
        self.assertTrue(jarvis_web._origin_allowed("http://localhost:8765", "localhost:8765"))
        self.assertTrue(jarvis_web._origin_allowed("", "localhost:8765"))
        self.assertFalse(jarvis_web._origin_allowed("https://evil.example", "localhost:8765"))

    def test_backend_token_matching_rejects_weak_defaults(self):
        self.assertFalse(backend_main._token_is_strong("jarvis"))
        self.assertFalse(backend_main._token_matches("jarvis"))
        self.assertTrue(backend_main._token_is_strong("b" * backend_main.MIN_BACKEND_TOKEN_LENGTH))


if __name__ == "__main__":
    unittest.main()
