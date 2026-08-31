import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "src")))

from parityprobe.compare import (  # noqa: E402
    Thresholds, build_snapshot, compare_pair, overall_verdict, tokenize,
)
from parityprobe.fetcher import FetchResult  # noqa: E402
from parityprobe.tokens import estimate_cost  # noqa: E402


def make_snapshot(key, html, status=200, label=None, kind="human"):
    body = html.encode("utf-8")
    fr = FetchResult(
        identity_key=key, requested_url="http://x/", final_url="http://x/",
        status=status, reason="OK", ok=200 <= status < 300,
        headers={"Content-Type": "text/html; charset=utf-8"}, body=body,
    )
    return build_snapshot(fr, label or key, kind, html)


PAGE_A = """<html><body><h1>Title</h1>
<p>Alpha bravo charlie delta echo.</p>
<p>Foxtrot golf hotel india juliet.</p></body></html>"""

PAGE_B = """<html><body><h1>Title</h1>
<p>Alpha bravo charlie delta echo.</p>
<p>Foxtrot golf hotel india juliet kilo lima.</p></body></html>"""

PAGE_OTHER = """<html><body><h1>Totally different</h1>
<ul><li>quantum</li><li>basil</li><li>xylophone</li></ul></body></html>"""


class CompareTests(unittest.TestCase):
    def test_identical(self):
        a, b = make_snapshot("chrome", PAGE_A), make_snapshot("gptbot", PAGE_A, kind="ai-bot")
        pair = compare_pair(a, b, Thresholds())
        self.assertEqual(pair.verdict, "identical")
        self.assertTrue(pair.raw_equal)
        self.assertEqual(pair.visible_similarity, 1.0)

    def test_near_drift(self):
        a, b = make_snapshot("chrome", PAGE_A), make_snapshot("gptbot", PAGE_B, kind="ai-bot")
        pair = compare_pair(a, b, Thresholds())
        self.assertIn(pair.verdict, ("near-identical", "drift"))
        self.assertGreater(pair.visible_similarity, 0.5)
        self.assertGreaterEqual(pair.added_lines, 1)

    def test_divergent(self):
        a = make_snapshot("chrome", PAGE_A)
        b = make_snapshot("gptbot", PAGE_OTHER, kind="ai-bot")
        pair = compare_pair(a, b, Thresholds())
        self.assertEqual(pair.verdict, "divergent")
        self.assertLess(pair.jaccard, 0.5)

    def test_blocked_status(self):
        a = make_snapshot("chrome", PAGE_A)
        b = make_snapshot("gptbot", "<html><body>denied</body></html>", status=403, kind="ai-bot")
        pair = compare_pair(a, b, Thresholds())
        self.assertEqual(pair.verdict, "blocked")

    def test_tokenizer(self):
        toks = tokenize("Hello, world! 中文测试")
        self.assertIn("hello", toks)
        self.assertIn("中", toks)
        self.assertIn("文", toks)

    def test_overall_aggregation(self):
        a = make_snapshot("chrome", PAGE_A)
        ok_pair = compare_pair(a, make_snapshot("gptbot", PAGE_A, kind="ai-bot"), Thresholds())
        verdict, _ = overall_verdict([ok_pair])
        self.assertEqual(verdict, "pass")
        bad_pair = compare_pair(a, make_snapshot("claudebot", PAGE_OTHER, kind="ai-bot"), Thresholds())
        verdict2, _ = overall_verdict([ok_pair, bad_pair])
        self.assertEqual(verdict2, "fail")


class TokenEstimateTests(unittest.TestCase):
    def test_known_text(self):
        cost = estimate_cost("Hello world, 中文")
        self.assertEqual(cost.words, 2)
        self.assertEqual(cost.cjk_chars, 2)
        self.assertGreaterEqual(cost.estimated_tokens, 4)

    def test_empty(self):
        cost = estimate_cost("")
        self.assertEqual(cost.estimated_tokens, 0)


if __name__ == "__main__":
    unittest.main()
