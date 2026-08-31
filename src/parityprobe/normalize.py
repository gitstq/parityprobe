"""Deterministic HTML normalization and machine-directed content detection.

The goal is *not* to be a browser: it is to extract reproducible, comparable
views of a page using only the standard library:

* visible text (what a human reads)
* boilerplate text (nav / header / footer / aside)
* hidden blocks (display:none, sr-only, offscreen positioning ...)
* text that appears to address AI agents / crawlers directly
"""
from __future__ import annotations

import codecs
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Pattern, Sequence, Tuple

__all__ = ["NormalizedDocument", "HiddenBlock", "MachineFinding", "normalize", "decode_bytes", "apply_noise_filters"]

_REMOVED_TAGS = {"script", "style", "noscript", "template", "svg", "math"}
_BOILERPLATE_TAGS = {"header", "nav", "footer", "aside", "form"}
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "nav", "aside", "blockquote", "figcaption"}
_HIDDEN_CLASS = re.compile(r"(^|[\s_-])(sr-only|screen-reader-text|visually-hidden|visuallyhidden|offscreen|hidden)([\s_-]|$)", re.I)
_INLINE_STYLE_HIDDEN = re.compile(
    r"(display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)|opacity\s*:\s*0(?:\.0+)?\b|font-size\s*:\s*0(?:px|pt|em|rem)?\b|left\s*:\s*-?\d{3,}px|text-indent\s*:\s*-?\d{3,}px)",
    re.I,
)
_MACHINE_PATTERNS = [
    re.compile(r"if you are an?\s+[^.<\n]{0,80}?(?:ai agent|automated (?:system|agent|crawler|browser)|language model|large language model|ai|llm|gpt|chatgpt|claude|gemini|crawler|spider|bot)", re.I),
    re.compile(r"(?:ai agent|llm|large language model|automated (?:system|agent|crawler))[^.<\n]{0,120}?(?:instruction|prompt|should|must|ignore previous|read this|do not)", re.I),
    re.compile(r"(?:dear|attention)[^.<\n]{0,40}?(?:ai|llm|gpt|chatgpt|claude|agent|crawler|bot)", re.I),
    re.compile(r"(如果你是|若你是|致|敬告)[^。<\n]{0,40}?(AI|人工智能|大模型|大語言模型|大语言模型|智能体|智能體|機器人|机器人|爬蟲|爬虫|自動化|自动化)"),
]
_WS = re.compile(r"[ \t\r\f\v]+")
_CAPTCHA = re.compile(r"(captcha|are you a robot|verify you are human|人机验证|人機驗證|安全验证)", re.I)


@dataclass
class HiddenBlock:
    text: str
    reason: str
    tag: str
    chars: int


@dataclass
class MachineFinding:
    snippet: str
    location: str  # "hidden" | "visible" | "boilerplate"
    pattern: str


@dataclass
class NormalizedDocument:
    visible_text: str
    boilerplate_text: str
    hidden_blocks: List[HiddenBlock] = field(default_factory=list)
    machine_findings: List[MachineFinding] = field(default_factory=list)
    title: str = ""
    description: str = ""
    canonical: str = ""
    captcha_suspected: bool = False
    removed_chars: int = 0
    raw_chars: int = 0

    @property
    def hidden_text(self) -> str:
        return "\n".join(b.text for b in self.hidden_blocks if b.text)


def decode_body(body: bytes, headers: Optional[Dict[str, str]] = None) -> str:
    """Decode response bytes using header charset, BOM, meta charset, then UTF-8."""
    return decode_bytes(body, headers or {})[0]


def decode_bytes(body: bytes, headers: Dict[str, str]) -> Tuple[str, str]:
    encoding = ""
    ctype = ""
    for k, v in headers.items():
        if k.lower() == "content-type":
            ctype = v
            break
    m = re.search(r"charset=([\w\-:]+)", ctype, re.I)
    if m:
        encoding = m.group(1).strip().strip('"')
    if not encoding:
        if body.startswith(codecs.BOM_UTF8):
            encoding = "utf-8-sig"
        elif body.startswith((b"\xff\xfe", b"\xfe\xff")):
            encoding = "utf-16"
    if not encoding:
        head = body[:4096].decode("ascii", "ignore")
        mm = re.search(r'<meta[^>]+charset=["\']?([\w\-:]+)', head, re.I)
        if mm:
            encoding = mm.group(1)
    for candidate in [encoding, "utf-8", "latin-1"]:
        if not candidate:
            continue
        try:
            return body.decode(candidate, errors="strict"), candidate
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def _clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = _WS.sub(" ", text)
    return text.strip()


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.visible: List[str] = []
        self.boiler: List[str] = []
        self.hidden: List[HiddenBlock] = []
        self.removed_chars = 0
        self.title_parts: List[str] = []
        self._in_title = False
        self.description = ""
        self.canonical = ""
        # stack entries: (tag, bucket) where bucket is visible/boiler/hidden/removed
        self._stack: List[Tuple[str, str, str]] = []  # (tag, bucket, hidden_reason)
        self._hidden_buf: List[str] = []

    def _current_bucket(self) -> str:
        return self._stack[-1][1] if self._stack else "visible"

    def _hidden_reason(self, tag: str, attrs: Dict[str, str]) -> str:
        style = attrs.get("style", "")
        cls = attrs.get("class", "")
        if tag in _REMOVED_TAGS:
            return ""
        if tag == "input" and attrs.get("type", "").lower() == "hidden":
            return "input[type=hidden]"
        if attrs.get("aria-hidden", "").lower() == "true":
            return "aria-hidden=true"
        if attrs.get("hidden") is not None:
            return "hidden-attribute"
        if cls and _HIDDEN_CLASS.search(cls):
            return f"hidden-class:{_HIDDEN_CLASS.search(cls).group(2)}"
        if style and _INLINE_STYLE_HIDDEN.search(style):
            return f"hidden-style:{_INLINE_STYLE_HIDDEN.search(style).group(1).replace(' ', '')}"
        return ""

    def handle_starttag(self, tag, attrs_list):
        tag = tag.lower()
        attrs = {k.lower(): (v if v is not None else "") for k, v in attrs_list}
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = _clean_text(attrs.get("content", ""))
        if tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonical = attrs.get("href", "")
        if tag in _REMOVED_TAGS:
            self._stack.append((tag, "removed", ""))
            return
        parent = self._current_bucket()
        reason = self._hidden_reason(tag, attrs)
        if parent == "removed":
            bucket = "removed"
        elif reason:
            bucket = "hidden"
        elif parent == "hidden":
            bucket = "hidden"
            reason = self._stack[-1][2]
        elif tag in _BOILERPLATE_TAGS:
            bucket = "boiler"
        elif parent == "boiler":
            bucket = "boiler"
        else:
            bucket = "visible"
        self._stack.append((tag, bucket, reason))
        if tag in _BLOCK_TAGS:
            self._emit("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        # pop nearest matching tag (HTML is messy; tolerate mismatches)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                start = self._stack[i]
                if start[1] == "hidden":
                    text = _clean_text(" ".join(self._hidden_buf))
                    if text:
                        self.hidden.append(HiddenBlock(text=text, reason=start[2] or "hidden", tag=start[0], chars=len(text)))
                    self._hidden_buf = []
                del self._stack[i:]
                break
        if tag in _BLOCK_TAGS:
            self._emit("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
            return
        bucket = self._current_bucket()
        if bucket == "removed":
            self.removed_chars += len(data)
            return
        if bucket == "hidden":
            self._hidden_buf.append(data)
            return
        self._emit(data, bucket)

    def _emit(self, data: str, bucket: Optional[str] = None):
        bucket = bucket or self._current_bucket()
        if bucket == "visible":
            self.visible.append(data)
        elif bucket == "boiler":
            self.boiler.append(data)

    @property
    def title(self) -> str:
        return _clean_text(" ".join(self.title_parts))


def _join_lines(parts: Sequence[str]) -> str:
    text = "".join(parts)
    lines = [_clean_text(line) for line in text.split("\n")]
    out: List[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank and out:
                out.append("")
            blank = True
        else:
            out.append(line)
            blank = False
    return "\n".join(out).strip()


def apply_noise_filters(text: str, patterns: Sequence[Pattern[str]]) -> str:
    """Remove volatile spans (timestamps, CSRF nonces ...) for stable comparison."""
    out = text
    for pat in patterns:
        out = pat.sub("", out)
    # re-collapse whitespace introduced by removals
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def find_machine_text(text: str, location: str) -> List[MachineFinding]:
    findings: List[MachineFinding] = []
    for pat in _MACHINE_PATTERNS:
        for m in pat.finditer(text):
            # Keep a readable context window around the trigger instead of only
            # the (often very short) matched span.
            end = min(len(text), m.end() + 160)
            snippet = _clean_text(text[m.start():end])[:240]
            if snippet:
                findings.append(MachineFinding(snippet=snippet, location=location, pattern=pat.pattern[:60]))
    return findings


def normalize(html_text: str, noise_patterns: Optional[Sequence[Pattern[str]]] = None) -> NormalizedDocument:
    """Turn raw HTML into a :class:`NormalizedDocument`."""
    parser = _PageParser()
    parser.feed(html_text)
    parser.close()
    # Flush any unterminated hidden block (tolerant of truncated pages)
    if parser._hidden_buf:
        text = _clean_text(" ".join(parser._hidden_buf))
        if text:
            parser.hidden.append(HiddenBlock(text=text, reason="unclosed", tag="", chars=len(text)))

    visible = _join_lines(parser.visible)
    boiler = _join_lines(parser.boiler)
    if noise_patterns:
        visible = apply_noise_filters(visible, noise_patterns)
        boiler = apply_noise_filters(boiler, noise_patterns)

    doc = NormalizedDocument(
        visible_text=visible,
        boilerplate_text=boiler,
        hidden_blocks=parser.hidden,
        title=parser.title,
        description=parser.description,
        canonical=parser.canonical,
        removed_chars=parser.removed_chars,
        raw_chars=len(html_text),
    )
    doc.machine_findings.extend(find_machine_text(visible, "visible"))
    doc.machine_findings.extend(find_machine_text(boiler, "boilerplate"))
    doc.machine_findings.extend(find_machine_text(doc.hidden_text, "hidden"))
    # Deduplicate overlapping pattern hits on the same snippet/location.
    seen = set()
    unique: List[MachineFinding] = []
    for f in doc.machine_findings:
        key = (f.location, f.snippet[:120])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    doc.machine_findings = unique
    doc.captcha_suspected = bool(_CAPTCHA.search(visible) or _CAPTCHA.search(doc.hidden_text))
    return doc
