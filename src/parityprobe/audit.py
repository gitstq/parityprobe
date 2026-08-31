"""Audit orchestration: fetch every identity concurrently and assemble reports."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from .compare import (
    PairComparison,
    Snapshot,
    Thresholds,
    build_snapshot,
    compare_pair,
    overall_verdict,
)
from .fetcher import fetch
from .identities import Identity
from .normalize import decode_bytes

__all__ = ["AuditOptions", "AuditReport", "audit_url", "audit_many", "compile_noise_patterns"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def compile_noise_filters(patterns: Sequence[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]


@dataclass
class AuditOptions:
    timeout: float = 15.0
    follow_redirects: bool = True
    verify_tls: bool = True
    noise_filters: Sequence[str] = field(default_factory=tuple)
    thresholds: Thresholds = field(default_factory=Thresholds)
    max_workers: int = 8

    @property
    def compiled_filters(self):
        return compile_noise_filters(self.noise_filters)


@dataclass
class AuditReport:
    url: str
    baseline_key: str
    started_at: str
    finished_at: str
    overall: str
    overall_notes: List[str]
    snapshots: List[Snapshot]
    pairs: List[PairComparison]
    options: Dict[str, object]
    hidden_findings: List[dict] = field(default_factory=list)

    def minimum_similarity(self) -> float:
        vals = [p.visible_similarity for p in self.pairs if p.verdict != "error"]
        return min(vals) if vals else 0.0

    def as_dict(self) -> dict:
        return {
            "tool": "parityprobe",
            "schema_version": 1,
            "url": self.url,
            "baseline": self.baseline_key,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "overall": self.overall,
            "overall_notes": self.overall_notes,
            "minimum_visible_similarity": round(self.minimum_similarity(), 4),
            "options": self.options,
            "identities": [
                {
                    "key": s.identity_key,
                    "label": s.identity_label,
                    "kind": s.kind,
                    "status": s.fetch.status,
                    "ok": s.fetch.ok,
                    "final_url": s.fetch.final_url,
                    "elapsed_ms": s.fetch.elapsed_ms,
                    "error": s.fetch.error,
                    "bytes": s.fetch.byte_size,
                    "visible_cost": s.visible_cost.as_dict(),
                    "boilerplate_cost": s.boilerplate_cost.as_dict(),
                    "title": s.doc.title if s.doc else "",
                    "hidden_blocks": [
                        {"text": b.text[:300], "reason": b.reason, "tag": b.tag, "chars": b.chars}
                        for b in (s.doc.hidden_blocks if s.doc else [])
                    ],
                    "machine_findings": [
                        {"snippet": f.snippet, "location": f.location}
                        for f in (s.doc.machine_findings if s.doc else [])
                    ],
                }
                for s in self.snapshots
            ],
            "comparisons": [p.as_dict() for p in self.pairs],
            "hidden_findings": self.hidden_findings,
        }


def _one(url: str, identity: Identity, options: AuditOptions) -> Snapshot:
    fr = fetch(
        url,
        identity,
        timeout=options.timeout,
        follow_redirects=options.follow_redirects,
        verify_tls=options.verify_tls,
    )
    decoded = ""
    if fr.body:
        decoded, _ = decode_bytes(fr.body, fr.headers)
    return build_snapshot(fr, identity.label, identity.kind, decoded, options.compiled_filters)


def audit_url(url: str, identities: Sequence[Identity], baseline_key: str = "chrome",
              options: Optional[AuditOptions] = None) -> AuditReport:
    """Run a full parity audit for one URL."""
    options = options or AuditOptions()
    started = _utc_now()
    keys = [i.key for i in identities]
    if baseline_key not in keys:
        raise ValueError(f"baseline identity {baseline_key!r} is not in the audit matrix {keys}")

    workers = max(1, min(options.max_workers, len(identities)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        snapshots = list(pool.map(lambda ident: _one(url, ident, options), identities))
    by_key: Dict[str, Snapshot] = {s.identity_key: s for s in snapshots}
    baseline = by_key[baseline_key]

    pairs: List[PairComparison] = []
    for s in snapshots:
        if s.identity_key == baseline_key:
            continue
        pairs.append(compare_pair(baseline, s, options.thresholds))
    pairs.sort(key=lambda p: p.visible_similarity)

    overall, notes = overall_verdict(pairs)
    finished = _utc_now()

    hidden_findings: List[dict] = []
    base_hidden = {b.text for b in (baseline.doc.hidden_blocks if baseline.doc else [])}
    for s in snapshots:
        if not s.doc:
            continue
        for block in s.doc.hidden_blocks:
            if s.identity_key != baseline_key and block.text in base_hidden:
                continue  # only surface identity-specific hidden content
            hidden_findings.append({
                "identity": s.identity_key,
                "reason": block.reason,
                "tag": block.tag,
                "chars": block.chars,
                "text": block.text[:400],
            })

    return AuditReport(
        url=url,
        baseline_key=baseline_key,
        started_at=started,
        finished_at=finished,
        overall=overall,
        overall_notes=notes,
        snapshots=snapshots,
        pairs=pairs,
        options={
            "timeout": options.timeout,
            "follow_redirects": options.follow_redirects,
            "verify_tls": options.verify_tls,
            "noise_filters": list(options.noise_filters),
            "thresholds": options.thresholds.__dict__,
        },
        hidden_findings=hidden_findings,
    )


def audit_many(urls: Sequence[str], identities: Sequence[Identity], baseline_key: str = "chrome",
               options: Optional[AuditOptions] = None) -> List[AuditReport]:
    """Run audits sequentially for a list of URLs (reports keep their input order)."""
    return [audit_url(u, identities, baseline_key, options) for u in urls]
