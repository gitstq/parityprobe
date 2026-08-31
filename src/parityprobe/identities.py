"""Client identity catalog for ParityProbe.

An :class:`Identity` describes *how* a request presents itself to a server:
user agent, negotiated headers and (optionally) Client Hints.  The catalog
ships with human browsers, search-engine crawlers and AI crawlers; custom
identities can be loaded from JSON.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

__all__ = ["Identity", "PRESETS", "preset_identities", "resolve_identities", "load_custom_identities"]


@dataclass(frozen=True)
class Identity:
    """A single, reusable HTTP client identity."""

    key: str
    label: str
    kind: str  # one of: human / search-bot / ai-bot / tool / custom
    user_agent: str
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    accept_language: str = "en-US,en;q=0.9"
    sec_ch_ua: Optional[str] = None
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: Optional[str] = None
    extra_headers: Dict[str, str] = field(default_factory=dict)
    note: str = ""

    def headers(self) -> Dict[str, str]:
        """Return the HTTP headers this identity sends."""
        h = {
            "User-Agent": self.user_agent,
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }
        if self.sec_ch_ua:
            h["Sec-CH-UA"] = self.sec_ch_ua
            h["Sec-CH-UA-Mobile"] = self.sec_ch_ua_mobile
        if self.sec_ch_ua_platform:
            h["Sec-CH-UA-Platform"] = self.sec_ch_ua_platform
        h.update(self.extra_headers)
        return h


# Preset user agents are pinned to known-good public strings and can be
# overridden at any time through a custom identity file.
_PRESET_LIST: List[Identity] = [
    Identity(
        key="chrome",
        label="Chrome (desktop human)",
        kind="human",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="8"',
        sec_ch_ua_platform='"Windows"',
        note="Baseline human visitor on a desktop.",
    ),
    Identity(
        key="safari",
        label="Safari (macOS human)",
        kind="human",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
        ),
        accept_language="en-US,en;q=0.9",
        note="Human visitor on macOS Safari.",
    ),
    Identity(
        key="googlebot",
        label="Googlebot",
        kind="search-bot",
        user_agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        accept_language="en-US,en;q=0.5",
        note="Google's classic crawler.",
    ),
    Identity(
        key="bingbot",
        label="Bingbot",
        kind="search-bot",
        user_agent="Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        note="Microsoft Bing crawler.",
    ),
    Identity(
        key="applebot",
        label="Applebot",
        kind="search-bot",
        user_agent="Mozilla/5.0 (compatible; Applebot/0.1; +http://www.apple.com/go/applebot)",
        note="Apple's crawler used by Search & Siri.",
    ),
    Identity(
        key="gptbot",
        label="GPTBot (OpenAI)",
        kind="ai-bot",
        user_agent=(
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; "
            "GPTBot/1.0; +https://openai.com/gptbot)"
        ),
        note="OpenAI crawler used for model training.",
    ),
    Identity(
        key="claudebot",
        label="ClaudeBot (Anthropic)",
        kind="ai-bot",
        user_agent="ClaudeBot/1.0 (+https://www.anthropic.com/crawler)",
        accept="*/*",
        note="Anthropic crawler used by Claude.",
    ),
    Identity(
        key="bytespider",
        label="Bytespider (ByteDance)",
        kind="ai-bot",
        user_agent="Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
        note="ByteDance crawler used by Doubao / TikTok services.",
    ),
    Identity(
        key="perplexitybot",
        label="PerplexityBot",
        kind="ai-bot",
        user_agent=(
            "Mozilla/5.0 (compatible; PerplexityBot/1.0; "
            "+https://perplexity.ai/perplexity-bot/)"
        ),
        note="Perplexity answer-engine crawler.",
    ),
    Identity(
        key="curl",
        label="curl / bare HTTP client",
        kind="tool",
        user_agent="curl/8.5.0",
        accept="*/*",
        accept_language="",
        note="Minimal command-line client baseline.",
    ),
]

PRESETS: Dict[str, Identity] = {i.key: i for i in _PRESET_LIST}

# A balanced default matrix: one human baseline plus the major AI/search bots.
DEFAULT_AUDIT_KEYS: List[str] = [
    "chrome",
    "googlebot",
    "gptbot",
    "claudebot",
    "bytespider",
    "perplexitybot",
]


def preset_identities() -> Dict[str, Identity]:
    """Return a copy of the preset identity catalog."""
    return dict(PRESETS)


def resolve_identities(
    keys: Optional[List[str]] = None,
    custom: Optional[Dict[str, Identity]] = None,
) -> List[Identity]:
    """Resolve a list of identity keys into :class:`Identity` objects.

    Custom identities take precedence over presets when keys collide.
    """
    custom = custom or {}
    selected = list(keys) if keys else list(DEFAULT_AUDIT_KEYS)
    out: List[Identity] = []
    seen = set()
    for key in selected:
        if key in seen:
            continue
        seen.add(key)
        if key in custom:
            out.append(custom[key])
        elif key in PRESETS:
            out.append(PRESETS[key])
        else:
            raise KeyError(f"unknown identity: {key!r} (known: {sorted(set(PRESETS) | set(custom))})")
    return out


def load_custom_identities(path: str | Path) -> Dict[str, Identity]:
    """Load custom identities from a JSON file.

    Expected schema: ``{"identities": [ {key, label, kind, user_agent, ...} ]}``.
    Unknown fields are ignored; ``extra_headers`` is merged verbatim.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = data.get("identities", data if isinstance(data, list) else [])
    out: Dict[str, Identity] = {}
    for item in raw:
        if "key" not in item or "user_agent" not in item:
            raise ValueError("each custom identity needs at least 'key' and 'user_agent'")
        ident = Identity(
            key=str(item["key"]),
            label=str(item.get("label", item["key"])),
            kind=str(item.get("kind", "custom")),
            user_agent=str(item["user_agent"]),
            accept=str(item.get("accept", Identity.accept)),
            accept_language=str(item.get("accept_language", Identity.accept_language)),
            sec_ch_ua=item.get("sec_ch_ua"),
            sec_ch_ua_mobile=str(item.get("sec_ch_ua_mobile", "?0")),
            sec_ch_ua_platform=item.get("sec_ch_ua_platform"),
            extra_headers=dict(item.get("extra_headers", {})),
            note=str(item.get("note", "")),
        )
        out[ident.key] = ident
    return out
