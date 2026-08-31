# Changelog

All notable changes to ParityProbe are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-31

### 🎉 Added
- First stable release.
- Multi-identity HTTP auditing on the Python standard library only (zero runtime dependencies).
- 10 built-in identities: Chrome, Safari, Googlebot, Bingbot, Applebot, GPTBot, ClaudeBot, Bytespider, PerplexityBot, curl; custom identities via JSON.
- Three-layer comparison: SHA-256 raw bytes, normalized DOM text, visible text (line diff + Jaccard + sequence similarity).
- Verdict taxonomy: `identical`, `near-identical`, `drift`, `divergent`, `blocked`, `redirected`, `error`, with hard-block / soft-block / CAPTCHA / identity-redirect detection and `pass / review / fail / incomplete` roll-up.
- Machine-directed hidden-content detection: nine hiding techniques plus EN/ZH phrase patterns, tagged by visible / boilerplate / hidden region.
- Noise-filter regexes, configurable similarity thresholds and `--fail-under` CI gate with documented exit codes.
- Reports: ANSI terminal text, machine-readable JSON, and a self-contained offline HTML report.
- CLI subcommands `audit`, `batch`, `identities`; importable library API (`audit_url`, `AuditOptions`, renderers).
- Transparent reading-cost estimate (bytes / chars / words / CJK chars / estimated tokens), explicitly labelled as approximation.
- gzip/deflate transport decoding, redirect-chain recording, TLS verification toggle, concurrent identity fetching.
- 35 fully offline tests over a deterministic fixture server (identical / cloaked / blocked / redirect / gzip / noise / CAPTCHA scenarios).
- Trilingual documentation: Simplified Chinese, Traditional Chinese, English.
