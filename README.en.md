# 🔭 ParityProbe · Web Content Parity Auditor

**🌐 Languages: [简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Zero Dependencies](https://img.shields.io/badge/runtime%20deps-0-success) ![License: MIT](https://img.shields.io/badge/License-MIT-green) ![Tests](https://img.shields.io/badge/tests-35%20passed-success) ![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

> Request one URL with a panel of honest client identities and **measure exactly what a site serves to human visitors, search-engine crawlers and AI crawlers**. Zero dependencies, offline-friendly, CI-ready — as both a CLI and a Python library.

---

## 🎉 Introduction

GPTBot, ClaudeBot, PerplexityBot, Bytespider — AI crawlers now fetch the web at massive scale, and developers, SEO engineers and compliance teams increasingly ask the same questions: *does this site serve different content to different visitors? Is there hidden copy written specifically for models?* Until now such claims mostly lived in screenshots. **What was missing was an externally reproducible, machine-readable measurement tool that also fits a CI pipeline.**

**ParityProbe** is that ruler:

- 🧑‍💻 Request the page once as a **human browser** (Chrome / Safari);
- 🤖 then request it again as **Googlebot / GPTBot / ClaudeBot / Bytespider / PerplexityBot** and friends;
- ⚖️ compare every pair at **three layers — raw bytes, normalized DOM text and visible text**;
- 🫥 surface **machine-directed content** humans never see: `display:none`, `sr-only`, offscreen positioning and phrases such as “If you are an AI agent…”;
- 📊 emit a terminal report, machine-readable JSON, or a **single self-contained HTML report**, with explicit verdicts and CI exit codes.

### 🌱 Inspiration & Originality

ParityProbe was inspired by community discussions (and an experimental Go implementation) about measuring what machine readers actually receive. **Not a single line of existing code was copied.** Only the product idea — external, multi-identity measurement — was kept. Everything is implemented from scratch on the Python standard library, with our own differentiators: a three-layer comparison model, machine-directed hidden-content detection, a verdict taxonomy with CI gating, batch matrix mode, an importable library API, and a fully offline deterministic test-suite.

### ✨ What makes it different

- **Zero runtime dependencies** — Python 3.9+ standard library only. No transitive dependencies, no supply-chain blind spots, runs in locked-down intranets.
- **Three-layer comparison** — byte hashes → normalized DOM text → visible text, so timestamps and CSRF nonces never masquerade as cloaking.
- **Machine-directed content detection** — hidden styles, `sr-only`, `aria-hidden`, offscreen placement, plus EN/ZH phrases that address models directly, tagged by where they appear.
- **Verdict taxonomy + CI exit codes** — `identical / near-identical / drift / divergent / blocked / redirected / error`, aggregated into `pass / review / fail / incomplete`, ready to gate a pipeline.
- **Three report formats** — ANSI tables, machine-readable JSON, and an offline HTML report with inlined CSS/JS you can hand to a colleague or attach as a build artifact.

---

## ✨ Features

- 🧩 **10 built-in identities**: two human browsers, three search bots, four AI bots and one bare HTTP client, with `Sec-CH-UA` client hints; extend with arbitrary custom identities (and headers) via JSON.
- ⚖️ **Three-layer parity comparison**: SHA-256 byte equality, line-level unified diff, dual similarity scores (token-set Jaccard + sequence ratio), plus negotiated-header diffs (`Vary`, `X-Robots-Tag`, `Cache-Control` …).
- 🫥 **Hidden-content excavation**: collects text from nine hiding techniques — `display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, negative offsets, `sr-only`-style classes, `aria-hidden`, the `hidden` attribute and `input[type=hidden]`.
- 🧠 **Machine-addressed phrase detection**: built-in EN/ZH patterns spot copy such as “If you are an AI/LLM/crawler…” and label whether it sits in visible, boilerplate or hidden regions.
- 🧹 **Noise filters**: pass repeatable regexes to strip request IDs, timestamps and tokens before comparison, so volatile nonces are never mistaken for differential serving.
- 🚦 **Smart verdicts**: distinguishes **hard blocks** (human 200, bot 403/429/451), **soft blocks** (bot receives under 15% of the visible text), **CAPTCHA challenges**, **identity-targeted redirects** and ordinary wording drift.
- 🏷️ **Transparent reading-cost estimate**: bytes, chars, words, CJK chars and an **estimated token count** — explicitly labelled an approximation, never passed off as a vendor tokenizer result.
- ⚡ **Concurrent fetching**: identities are fetched in a thread pool with deterministic output ordering; gzip/deflate are auto-decompressed, TLS verification is configurable, and full redirect chains are recorded.
- 📚 **CLI + library**: run `parityprobe audit` end-to-end, or `from parityprobe import audit_url` to embed it.
- 🧪 **35 offline tests**: a deterministic fixture server covers identical pages, cloaking, blocks, redirects, gzip, volatile noise and CAPTCHA — full regression without touching the network.

---

## 🚀 Quick Start

### 📋 Requirements

| Item | Requirement |
| --- | --- |
| Python | **3.9+** (verified on 3.9 / 3.10 / 3.11 / 3.12) |
| Third-party runtime dependencies | **None** |
| OS | Windows, macOS, Linux |
| Network | Needed only when auditing public sites; the test-suite is fully offline |

### 📦 Installation

```bash
# Option 1 — clone and install (registers the parityprobe command)
git clone https://github.com/gitstq/parityprobe.git
cd parityprobe
pip install .

# Option 2 — run without installation (src layout)
PYTHONPATH=src python -m parityprobe --version

# Option 3 — isolated install with pipx
pipx install .
```

### ⚡ First 60 seconds

```bash
# 1) List every built-in identity
parityprobe identities

# 2) Audit a page with the default matrix (human + five crawlers)
parityprobe audit https://example.com/

# 3) Pick identities and export a self-contained HTML report
parityprobe audit https://example.com/ \
  -i chrome -i googlebot -i gptbot -i claudebot \
  -f html -o report.html

# 4) Emit machine-readable JSON for downstream analysis
parityprobe audit https://example.com/ -f json -o report.json
```

Sample output (excerpt from a real fixture run; see [`examples/sample_report.txt`](examples/sample_report.txt) for the full report):

```text
ParityProbe audit · https://example.com/
Overall: PASS  baseline=chrome  min_similarity=1.000

KEY             KIND         STATUS    BYTES       TOK~
chrome          human        200       559         21
googlebot       search-bot   200       559         21
gptbot          ai-bot       200       559         21

IDENTITY        VERDICT      SIM       JACC
googlebot       identical    1.000     1.000   · byte-for-byte identical response
gptbot          identical    1.000     1.000   · byte-for-byte identical response
```

---

## 📖 Usage Guide

### 🧾 Subcommands

| Command | Purpose |
| --- | --- |
| `parityprobe audit <url>` | Audit a single URL |
| `parityprobe batch <url_file>` | Audit many URLs (one per line; `#` starts a comment) |
| `parityprobe identities` | List built-in (and custom) identities |

### 🎛️ Common `audit` options

| Option | Description |
| --- | --- |
| `-i, --identity` | Identity key to include (repeatable); defaults to the built-in matrix |
| `-b, --baseline` | Baseline identity every other identity is compared against (default `chrome`) |
| `-f, --format` | `text` (default) / `json` / `html` |
| `-o, --output` | Write the report to a file instead of stdout |
| `-c, --config` | JSON config file (see [`examples/config.example.json`](examples/config.example.json)) |
| `--custom` | Custom-identity JSON file (see [`examples/identities.example.json`](examples/identities.example.json)) |
| `--ignore` | Noise regex removed before comparison (repeatable) |
| `--timeout` | Per-request timeout in seconds (default 15) |
| `--no-redirects` | Do not follow 3xx responses (reveals identity-targeted redirects) |
| `--insecure` | Disable TLS verification (intranet self-signed cases only) |
| `--identical-threshold / --near-threshold / --divergent-threshold` | Similarity cut-offs (defaults 0.999 / 0.985 / 0.80) |
| `--fail-under` | Minimum-similarity gate; exit code 2 when violated (default 0.80) |

### 🧹 Remove noise to avoid false alarms

Values like `req-9f3a2c` or ISO timestamps change on every fetch and depress similarity. Strip them with `--ignore`:

```bash
parityprobe audit https://shop.example.com/product/42 \
  --ignore 'req-[0-9a-f]{8,}' \
  --ignore '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z' \
  --ignore 'csrf=[A-Za-z0-9._-]+'
```

### 🧑‍🎤 Custom identities

```json
{
  "identities": [
    {
      "key": "internal-monitor",
      "label": "Internal uptime monitor",
      "kind": "tool",
      "user_agent": "AcmeMonitor/3.1 (+https://example.com/monitor)",
      "extra_headers": { "Authorization": "Bearer replace-me" }
    }
  ]
}
```

```bash
parityprobe audit https://example.com/ --custom my-identities.json \
  -i chrome -i internal-monitor
```

### 🧱 Verdict taxonomy

| Verdict | Meaning |
| --- | --- |
| `identical` | Byte-for-byte equal, or visible similarity ≥ 0.999 |
| `near-identical` | Similarity ≥ 0.985; only wording/boilerplate micro-drift |
| `drift` | Similarity ≥ 0.80; visible differences but structure holds |
| `divergent` | Similarity below 0.80; materially different content |
| `blocked` | Baseline got 2xx while this identity got 401/403/429/451, or hit a CAPTCHA challenge |
| `redirected` | This identity was sent to a different endpoint than the baseline |
| `error` | Request failed (DNS, TLS, timeout); captured, never fatal to the whole run |

Overall roll-up: any `blocked / divergent / soft-block` → **fail**; any `drift / redirected / near-identical` → **review**; all equivalent → **pass**; unfinished measurements → **incomplete**.

### 🚪 Exit codes (CI-friendly)

| Code | Meaning |
| --- | --- |
| `0` | Audit completed without triggering a failure |
| `1` | Tool-level error (bad arguments, missing file, incomplete measurement) |
| `2` | Parity failure (overall fail, or minimum similarity below `--fail-under`) |

### 🐍 Use it as a Python library

```python
from parityprobe import AuditOptions, audit_url, resolve_identities, render_json

ids = resolve_identities(["chrome", "gptbot", "claudebot"])
opts = AuditOptions(timeout=10, noise_filters=[r"req-[0-9a-f]+"])
report = audit_url("https://example.com/", ids, baseline_key="chrome", options=opts)

print(report.overall)              # pass / review / fail / incomplete
print(report.minimum_similarity()) # 0.0 - 1.0
for pair in report.pairs:
    print(pair.other_key, pair.verdict, pair.visible_similarity, pair.reasons)

print(render_json(report, indent=2))  # machine-readable report
```

### 📈 Batch audits

```bash
parityprobe batch examples/urls.example.txt -f json -o batch.json
parityprobe batch urls.txt       # terminal matrix: overall verdict + worst identity per URL
```

### 🖼️ Demo artifacts

- Terminal sample: [`examples/sample_report.txt`](examples/sample_report.txt)
- JSON sample: [`examples/sample_report.json`](examples/sample_report.json)
- **HTML sample (open in a browser after downloading)**: [`examples/sample_report.html`](examples/sample_report.html)
- Screenshots / screencasts: community PRs welcome (please use `docs/demo/`).

---

## 💡 Design Notes & Roadmap

### 🏗️ Architecture

```
src/parityprobe/
├── identities.py   # Identity catalog: UA / Accept / Sec-CH-UA / custom headers
├── fetcher.py      # Stdlib HTTP layer: concurrency, redirect chains, gzip, TLS
├── normalize.py    # HTML parsing: visible text / boilerplate / hidden blocks / machine phrases
├── compare.py      # Three-layer compare: byte hash, line diff, Jaccard, sequence ratio, verdicts
├── tokens.py       # Transparent reading-cost estimate (labelled approximation)
├── audit.py        # Orchestration: concurrent scheduling, snapshots, overall verdict
├── report.py       # text / json / self-contained html renderers
└── cli.py          # argparse CLI: audit / batch / identities
```

### 🧭 Key trade-offs

1. **Why zero third-party dependencies?** An auditor must itself be auditable. No transitive dependencies means no supply-chain blind spots and instant operation in air-gapped environments; the standard library (`urllib`, `html.parser`, `difflib`, `ssl`, `concurrent.futures`) covers everything needed.
2. **Why no real browser rendering?** External measurement values reproducibility and low overhead. A single HTTP exchange reveals what the server *chooses* to serve — which is exactly the parity question. Rendering-layer differences are a separate problem, slated for a future optional plugin.
3. **Why estimated tokens only?** Exact tokenization pins you to vendor vocabularies, conflicting with zero-dependency and offline goals. We publish the formula (latin word-pieces + CJK characters + punctuation runs) and label every number as an estimate.
4. **Why not render a verdict of guilt?** The tool presents evidence and graded classifications; whether differential serving is improper is for the operator to decide in context — measurement and adjudication stay separate.

### 🗺️ Roadmap

- [ ] v1.1 — Markdown / plain-text identity (`Accept: text/markdown`) comparison and sitemap-driven batch mode
- [ ] v1.2 — Pluggable comparator interface with optional local-model semantic similarity (optional dependency)
- [ ] v1.3 — Historical snapshots: parity-drift trends for one URL over time
- [ ] v1.4 — HAR import and browser-extension bridge to cover the rendering layer
- [ ] Long term — community-maintained multilingual machine-phrase pattern library (directory-based `patterns/`)

### 🙋 How to contribute

New crawler presets, machine-phrase patterns in more languages, normalization improvements, and redacted real-world cases are high-value PRs. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📦 Packaging & Deployment

ParityProbe is a **library / CLI** project (pure Python, interpreted, cross-platform), so no per-platform binaries are required.

### 🏗️ Build wheel / sdist

```bash
pip install build
python -m build          # produces dist/parityprobe-1.0.0-py3-none-any.whl and .tar.gz
pip install dist/parityprobe-1.0.0-py3-none-any.whl
```

The wheel is tagged `py3-none-any` — **one artifact for Windows, macOS and Linux**.

### ▶️ Deploy without installing

Copy the `src/parityprobe` directory and run `PYTHONPATH=src python -m parityprobe ...` — ideal for read-only containers and audit bastion hosts.

### 🤖 As a CI quality gate (GitHub Actions)

```yaml
name: content-parity-check
on: [schedule, workflow_dispatch]
jobs:
  parity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install git+https://github.com/gitstq/parityprobe.git
      - run: parityprobe audit https://your-site.example/ -f html -o parity.html
      - uses: actions/upload-artifact@v4
        with: { name: parity-report, path: parity.html }
```

### ✅ Run the tests locally

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
# 35 tests — fully offline, finishes in about 3 seconds
```

---

## 🤝 Contributing

1. 🍴 Fork and branch from `main`; suggested names are `feat/xxx`, `fix/xxx`.
2. 💾 Follow **Angular Conventional Commits**: `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`.
3. 🧪 Add `tests/` coverage for new behavior (prefer the fixture server to stay offline); keep `python -m unittest discover -s tests` green.
4. 🧹 Honor the zero-runtime-dependency rule — reach for the standard library first; genuinely optional extras belong in `optional-dependencies`.
5. 🔀 In your PR, explain motivation, usage and how you tested it; verdict-logic changes must also update the taxonomy table in the docs.

Issues, identity presets and redacted real-world cases are equally welcome. The full guide lives in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📄 License

Released under the **[MIT License](LICENSE)** — free to use, modify, distribute and commercialize, provided the copyright and permission notice are retained. ParityProbe is intended for compliant auditing of sites **you own or are authorized to test**; operators are responsible for ensuring their audits respect local law and target-site terms.
