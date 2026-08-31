# Contributing to ParityProbe

感谢你愿意参与 ParityProbe / Thanks for taking the time to contribute!

- 中文贡献者请直接用中文描述 Issue 与 PR，没有语言门槛。
- English contributions are equally welcome.

## 🧭 Ground rules

1. **Zero runtime dependencies is a feature.** Reach for the Python standard library first. New third-party runtime dependencies are accepted only when the standard library genuinely cannot do the job, and must be added as *optional* dependencies (`[project.optional-dependencies]`), never required ones.
2. **Everything testable offline.** Tests must run without internet access — extend `tests/fixtures_server.py` when you need a new server behaviour instead of hitting real websites.
3. **Supported runtimes: Python 3.9 – 3.12, Windows / macOS / Linux.** Do not use Unix-only APIs on hot paths; do not use syntax newer than 3.9.
4. **Measurement, not judgement.** The tool reports evidence and graded verdicts; it must not editorialize about the target site.

## 🌿 Development workflow

```bash
git clone https://github.com/gitstq/parityprobe.git
cd parityprobe
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

# Run the whole suite (no network needed, ~3 seconds)
PYTHONPATH=src python -m unittest discover -s tests -v
```

Before opening a PR:

- [ ] All 35+ existing tests still pass and your new tests pass.
- [ ] `python -m py_compile src/parityprobe/*.py tests/*.py` is clean.
- [ ] Public behaviour is documented in **all three READMEs** (`README.md`, `README.zh-TW.md`, `README.en.md`) when it changes.
- [ ] New CLI options appear in the option tables; new verdicts appear in the verdict-taxonomy tables.

## 💬 Commit conventions (Angular)

Use Conventional Commits with Angular-style types:

| Prefix | Use for |
| --- | --- |
| `feat:` | New user-facing capability |
| `fix:` | Bug fix |
| `docs:` | Documentation only (READMEs, examples, comments) |
| `refactor:` | Internal restructuring without behaviour change |
| `test:` | Adding or correcting tests |
| `chore:` | Packaging, CI, tooling |

Examples: `feat: add baiduspider identity preset`, `fix: preserve redirect chain under --no-redirects`, `docs: clarify token estimation limits`.

## 🧩 Adding a new identity preset

1. Add an `Identity(...)` entry in `src/parityprobe/identities.py` with a stable `key`, correct `kind` (`human` / `search-bot` / `ai-bot` / `tool`) and a sourced, current user-agent string.
2. Add or extend a test in `tests/test_identities.py`.
3. List it in `parityprobe identities` output automatically; mention it in each README's feature section if notable.

## 🧠 Adding a machine-directed phrase pattern

1. Extend `_MACHINE_PATTERNS` in `src/parityprobe/normalize.py` — avoid catastrophic backtracking; anchor character classes tightly.
2. Add a fixture case in `tests/test_normalize.py` with both a positive and (where possible) a negative example.
3. Patterns should catch *addressing a machine*, not merely mentioning AI.

## 🐛 Reporting issues

Please include: ParityProbe version (`parityprobe --version`), Python version, OS, the exact command, expected vs actual output, and—for false verdicts—a **redacted** sample page or a minimal fixture reproduction. Do not paste private response bodies containing credentials.

## 🔀 Pull request checklist

- Clear title in Conventional Commits format.
- Description: motivation, approach, testing evidence.
- One logical change per PR; keep diffs reviewable.
- No generated caches (`__pycache__`, `*.egg-info`, `dist/`) committed.

## 📄 License

By contributing, you agree your contribution is licensed under the project's MIT License.
