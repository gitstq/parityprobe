import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)
sys.path.insert(0, HERE)

from fixtures_server import start_fixture_server  # noqa: E402


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_fixture_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _run(self, *args):
        env = dict(os.environ, PYTHONPATH=SRC)
        proc = subprocess.run(
            [sys.executable, "-m", "parityprobe", *args],
            capture_output=True, text=True, env=env, timeout=30,
        )
        return proc

    def test_identities_list(self):
        proc = self._run("identities")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("gptbot", proc.stdout)
        self.assertIn("claudebot", proc.stdout)

    def test_audit_json_pass(self):
        proc = self._run("audit", self.base + "/same", "-f", "json",
                         "-i", "chrome", "-i", "gptbot")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["overall"], "pass")
        self.assertEqual(len(data["identities"]), 2)

    def test_audit_blocked_exit_code(self):
        proc = self._run("audit", self.base + "/blocked", "-f", "json",
                         "-i", "chrome", "-i", "gptbot")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["overall"], "fail")

    def test_html_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.html")
            proc = self._run("audit", self.base + "/same", "-f", "html", "-o", out,
                             "-i", "chrome", "-i", "gptbot")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(out, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("ParityProbe", content)

    def test_batch_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            urls = os.path.join(tmp, "urls.txt")
            with open(urls, "w", encoding="utf-8") as fh:
                fh.write(f"# comment\n{self.base}/same\n{self.base}/blocked\n")
            proc = self._run("batch", urls, "-i", "chrome", "-i", "gptbot")
            self.assertEqual(proc.returncode, 2)
            self.assertIn("OVERALL", proc.stdout)


if __name__ == "__main__":
    unittest.main()
