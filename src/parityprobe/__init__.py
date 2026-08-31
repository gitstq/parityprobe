"""ParityProbe — audit what a website serves to humans vs AI/search crawlers.

Public API:

    from parityprobe import AuditOptions, Identity, PRESETS, audit_url, resolve_matrix

    report = audit_url("https://example.com", resolve_matrix())
    print(report.overall)
"""
from __future__ import annotations

from .audit import AuditOptions, AuditReport, audit_many, audit_url
from .compare import PairComparison, Snapshot, Thresholds
from .fetcher import FetchResult, fetch
from .identities import PRESETS, Identity, resolve_identities
from .normalize import NormalizedDocument, normalize
from .report import render_html, render_json, render_text

__version__ = "1.0.0"
__all__ = [
    "__version__",
    "AuditOptions",
    "AuditReport",
    "audit_url",
    "audit_many",
    "Thresholds",
    "PairComparison",
    "Snapshot",
    "FetchResult",
    "fetch",
    "Identity",
    "PRESETS",
    "resolve_identities",
    "NormalizedDocument",
    "normalize",
    "render_text",
    "render_json",
    "render_html",
]


def resolve_matrix(keys=None, custom=None):
    """Convenience wrapper around :func:`resolve_identities`."""
    return resolve_identities(keys, custom)
