import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "src")))

from parityprobe.identities import (  # noqa: E402
    PRESETS, load_custom_identities, resolve_identities,
)


class IdentityTests(unittest.TestCase):
    def test_preset_headers(self):
        chrome = PRESETS["chrome"]
        headers = chrome.headers()
        self.assertIn("Chrome/126", headers["User-Agent"])
        self.assertIn("Sec-CH-UA", headers)
        self.assertEqual(headers["Accept-Encoding"], "gzip, deflate")

    def test_default_matrix(self):
        ids = resolve_identities()
        keys = [i.key for i in ids]
        self.assertEqual(keys[0], "chrome")
        self.assertIn("gptbot", keys)
        self.assertIn("claudebot", keys)
        self.assertEqual(len(keys), 6)

    def test_unknown_raises(self):
        with self.assertRaises(KeyError):
            resolve_identities(["nope"])

    def test_custom_identity_file(self):
        payload = {"identities": [{
            "key": "mybot", "label": "My Bot", "kind": "ai-bot",
            "user_agent": "MyBot/2.0", "extra_headers": {"X-Token": "abc"},
        }]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(payload, fh)
            path = fh.name
        try:
            custom = load_custom_identities(path)
            ids = resolve_identities(["chrome", "mybot"], custom)
            self.assertEqual(ids[1].headers()["X-Token"], "abc")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
