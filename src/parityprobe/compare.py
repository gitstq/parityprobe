"""Three-layer comparison: raw bytes / normalized HTML / visible text."""
from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .fetcher import FetchResult, same_endpoint
from .normalize import NormalizedDocument
from .tokens import CostEstimate, estimate_cost

__all__ = ["Snapshot", "Thresholds", "PairComparison", "build_snapshot", "compare_pair", "overall_verdict", "tokenize"]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9]+)*|[\u3400-\u9fff]")
_BLOCKED_STATUS = {401, 403, 429, 451}
_DIFF_CAP = 600
_COMPARED_HEADERS = (
    "content-type", "cache-control", "vary", "x-robots-tag", "link",
    "content-language", "content-security-policy", "server", "x-frame-options",
)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass
class Snapshot:
    identity_key: str
    identity_label: str
    kind: str
    fetch: FetchResult
    doc: Optional[NormalizedDocument]
    visible_cost: CostEstimate
    boilerplate_cost: CostEstimate

    @property
    def visible_text(self) -> str:
        return self.doc.visible_text if self.doc else ""

    @property
    def hidden_text(self) -> str:
        return self.doc.hidden_text if self.doc else ""


def build_snapshot(fetch: FetchResult, label: str, kind: str, decoded_html: str,
                   noise_patterns: Optional[Sequence[re.Pattern]] = None) -> Snapshot:
    from .normalize import normalize  # local import keeps module import order simple
    doc = normalize(decoded_html, noise_patterns) if decoded_html is not None else None
    return Snapshot(
        identity_key=fetch.identity_key,
        identity_label=label,
        kind=kind,
        fetch=fetch,
        doc=doc,
        visible_cost=estimate_cost(doc.visible_text if doc else "", fetch.byte_size),
        boilerplate_cost=estimate_cost(doc.boilerplate_text if doc else ""),
    )


@dataclass
class Thresholds:
    identical: float = 0.999
    near: float = 0.985
    divergent: float = 0.80


@dataclass
class PairComparison:
    baseline_key: str
    other_key: str
    other_label: str
    other_kind: str
    status_baseline: int
    status_other: int
    final_baseline: str
    final_other: str
    raw_equal: bool
    sha_baseline: str
    sha_other: str
    bytes_baseline: int
    bytes_other: int
    visible_similarity: float
    jaccard: float
    added_lines: int
    removed_lines: int
    diff_preview: List[str] = field(default_factory=list)
    changed_headers: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    hidden_blocks_baseline: int = 0
    hidden_blocks_other: int = 0
    machine_findings_other: List[dict] = field(default_factory=list)
    captcha_suspected: bool = False
    soft_blocked: bool = False
    verdict: str = "error"
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "baseline": self.baseline_key,
            "identity": self.other_key,
            "label": self.other_label,
            "kind": self.other_kind,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "status": {"baseline": self.status_baseline, "other": self.status_other},
            "final_url": {"baseline": self.final_baseline, "other": self.final_other},
            "raw_equal": self.raw_equal,
            "sha256": {"baseline": self.sha_baseline, "other": self.sha_other},
            "bytes": {"baseline": self.bytes_baseline, "other": self.bytes_other,
                      "delta": self.bytes_other - self.bytes_baseline},
            "visible_similarity": round(self.visible_similarity, 4),
            "token_jaccard": round(self.jaccard, 4),
            "line_changes": {"added": self.added_lines, "removed": self.removed_lines},
            "changed_headers": {k: list(v) for k, v in self.changed_headers.items()},
            "hidden_blocks": {"baseline": self.hidden_blocks_baseline, "other": self.hidden_blocks_other},
            "machine_findings": self.machine_findings_other,
            "captcha_suspected": self.captcha_suspected,
            "soft_blocked": self.soft_blocked,
            "diff_preview": self.diff_preview,
        }


def _jaccard(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _header_diff(fa: FetchResult, fb: FetchResult) -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    ha = {k.lower(): v for k, v in fa.headers.items()}
    hb = {k.lower(): v for k, v in fb.headers.items()}
    for key in _COMPARED_HEADERS:
        va, vb = ha.get(key, ""), hb.get(key, "")
        if va != vb:
            out[key] = (va, vb)
    return out


def compare_pair(base: Snapshot, other: Snapshot, thresholds: Thresholds) -> PairComparison:
    fb, fo = base.fetch, other.fetch
    sha_b = hashlib.sha256(fb.body).hexdigest()
    sha_o = hashlib.sha256(fo.body).hexdigest()
    raw_equal = sha_b == sha_o

    text_b, text_o = base.visible_text, other.visible_text
    lines_b, lines_o = text_b.splitlines(), text_o.splitlines()
    matcher = difflib.SequenceMatcher(a=lines_b, b=lines_o, autojunk=False)
    sim = matcher.ratio() if (lines_b or lines_o) else 1.0
    jac = _jaccard(text_b, text_o)

    diff = list(difflib.unified_diff(lines_b, lines_o, fromfile=base.identity_key, tofile=other.identity_key, lineterm=""))
    added = sum(1 for ln in diff if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff if ln.startswith("-") and not ln.startswith("---"))

    pair = PairComparison(
        baseline_key=base.identity_key,
        other_key=other.identity_key,
        other_label=other.identity_label,
        other_kind=other.kind,
        status_baseline=fb.status,
        status_other=fo.status,
        final_baseline=fb.final_url,
        final_other=fo.final_url,
        raw_equal=raw_equal,
        sha_baseline=sha_b,
        sha_other=sha_o,
        bytes_baseline=fb.byte_size,
        bytes_other=fo.byte_size,
        visible_similarity=sim,
        jaccard=jac,
        added_lines=added,
        removed_lines=removed,
        diff_preview=diff[:_DIFF_CAP],
        changed_headers=_header_diff(fb, fo),
        hidden_blocks_baseline=len(base.doc.hidden_blocks) if base.doc else 0,
        hidden_blocks_other=len(other.doc.hidden_blocks) if other.doc else 0,
        machine_findings_other=[
            {"snippet": f.snippet, "location": f.location}
            for f in (other.doc.machine_findings if other.doc else [])
        ],
        captcha_suspected=bool(other.doc and other.doc.captcha_suspected),
    )
    pair.verdict, pair.reasons = _classify(base, other, pair, thresholds)
    return pair


def _classify(base: Snapshot, other: Snapshot, pair: PairComparison, t: Thresholds) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    fo = other.fetch
    if fo.error:
        reasons.append(f"request failed: {fo.error}")
        return "error", reasons
    if base.fetch.error:
        reasons.append("baseline request failed; cannot compare")
        return "error", reasons

    if base.fetch.ok and fo.status in _BLOCKED_STATUS:
        reasons.append(f"baseline HTTP {base.fetch.status} but identity got HTTP {fo.status}")
        return "blocked", reasons

    if not same_endpoint(base.fetch.final_url, fo.final_url):
        reasons.append(f"served from a different endpoint: {fo.final_url}")
        return "redirected", reasons

    if pair.captcha_suspected and pair.visible_similarity < 0.6:
        reasons.append("challenge / CAPTCHA-style page served to this identity")
        return "blocked", reasons

    # Soft block: tiny stub compared to the full baseline page.
    if base.visible_cost.chars > 400 and other.visible_cost.chars:
        ratio = other.visible_cost.chars / max(base.visible_cost.chars, 1)
        if ratio < 0.15 and pair.visible_similarity < 0.5:
            pair.soft_blocked = True
            reasons.append(f"response is only {ratio:.1%} of baseline visible text")

    if pair.raw_equal:
        reasons.append("byte-for-byte identical response")
        return "identical", reasons
    if pair.visible_similarity >= t.identical:
        reasons.append("only non-visible / whitespace differences")
        return "identical", reasons
    if pair.visible_similarity >= t.near:
        reasons.append("minor wording or boilerplate drift")
        return "near-identical", reasons
    if pair.visible_similarity >= t.divergent:
        reasons.append("visible content differs but overall structure stays similar")
        return "drift", reasons
    reasons.append(f"visible similarity {pair.visible_similarity:.3f} below divergent threshold {t.divergent}")
    return "divergent", reasons


def overall_verdict(pairs: Sequence[PairComparison]) -> Tuple[str, List[str]]:
    """Aggregate pair verdicts into pass / review / fail / incomplete."""
    bad = [p for p in pairs if p.verdict in ("blocked", "divergent")]
    warn = [p for p in pairs if p.verdict in ("drift", "redirected", "near-identical")]
    errored = [p for p in pairs if p.verdict == "error"]
    soft = [p for p in pairs if p.soft_blocked]
    notes: List[str] = []
    if bad or soft:
        for p in bad + soft:
            notes.append(f"{p.other_key}: {p.verdict}")
        return "fail", notes
    if errored:
        for p in errored:
            notes.append(f"{p.other_key}: {p.reasons[0] if p.reasons else 'error'}")
        return "incomplete", notes
    if warn:
        for p in warn:
            notes.append(f"{p.other_key}: {p.verdict}")
        return "review", notes
    return "pass", ["all identities received equivalent content"]
