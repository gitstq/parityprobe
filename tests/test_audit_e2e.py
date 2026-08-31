import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "src")))
sys.path.insert(0, os.path.abspath(HERE))

from parityprobe.audit import AuditOptions, audit_url  # noqa: E402
from parityprobe.fetcher import fetch  # noqa: E402
from parityprobe.identities import resolve_identities  # noqa: E402
from parityprobe.report import render_html, render_json, render_text  # noqa: E402
from fixtures_server import start_fixture_server  # noqa: E402

IDS = resolve_identities(["chrome", "gptbot", "bytespider"])


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_fixture_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _audit(self, path, options=None):
        return audit_url(self.base + path, IDS, baseline_key="chrome", options=options or AuditOptions())

    def test_same_is_pass(self):
        report = self._audit("/same")
        self.assertEqual(report.overall, "pass", report.overall_notes)
        for pair in report.pairs:
            self.assertEqual(pair.verdict, "identical")

    def test_cloaked_fails_with_hidden_machine_text(self):
        report = self._audit("/cloaked")
        self.assertEqual(report.overall, "fail")
        verdicts = {p.other_key: p.verdict for p in report.pairs}
        self.assertIn(verdicts["gptbot"], ("divergent", "drift"))
        self.assertTrue(any("AI agent" in f.get("text", "") for f in report.hidden_findings),
                        report.hidden_findings)

    def test_blocked_bots(self):
        report = self._audit("/blocked")
        self.assertEqual(report.overall, "fail")
        for pair in report.pairs:
            self.assertEqual(pair.verdict, "blocked")
            self.assertEqual(pair.status_other, 403)

    def test_redirect_detected(self):
        report = self._audit("/redirect")
        for pair in report.pairs:
            self.assertEqual(pair.verdict, "redirected")
            self.assertIn("/landed-elsewhere", pair.final_other)

    def test_gzip_decoded(self):
        report = self._audit("/gzip")
        self.assertEqual(report.overall, "pass")
        for snap in report.snapshots:
            self.assertIn("Compressed page", snap.visible_text)

    def test_noise_filters_stabilize(self):
        noisy = self._audit("/noise")
        self.assertNotEqual(noisy.overall, "pass")
        opts = AuditOptions(noise_filters=[r"req-[0-9a-f]+", r"\d{2}:\d{2}:\d{2}Z"])
        cleaned = self._audit("/noise", opts)
        self.assertEqual(cleaned.overall, "pass", cleaned.overall_notes)

    def test_reports_render(self):
        report = self._audit("/cloaked")
        text = render_text(report, color=False)
        self.assertIn("ParityProbe audit", text)
        js = render_json(report)
        self.assertIn('"tool": "parityprobe"', js)
        page = render_html(report)
        self.assertIn("<!DOCTYPE html>", page)
        self.assertIn("Pairwise comparison", page)

    def test_fetcher_no_redirect(self):
        from parityprobe.identities import PRESETS
        r = fetch(self.base + "/redirect", PRESETS["gptbot"], follow_redirects=False)
        self.assertEqual(r.status, 302)

    def test_fetcher_network_error_is_captured(self):
        from parityprobe.identities import PRESETS
        r = fetch("http://127.0.0.1:1/never", PRESETS["chrome"], timeout=2)
        self.assertEqual(r.status, 0)
        self.assertIsNotNone(r.error)


if __name__ == "__main__":
    unittest.main()
