"""ParityProbe command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from . import __version__
from .audit import AuditOptions, AuditReport, audit_many, audit_url
from .compare import Thresholds
from .identities import Identity, PRESETS, load_custom_identities, preset_identities, resolve_identities
from .report import render_html, render_json, render_text

__all__ = ["main", "build_parser"]

EXIT_OK = 0
EXIT_TOOL_ERROR = 1
EXIT_PARITY_FAIL = 2


def _read_urls(path: str) -> List[str]:
    urls: List[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line.split()[0])
    return urls


def _load_config(path: Optional[str]) -> dict:
    if not path:
        return {}
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_options(args: argparse.Namespace, config: dict) -> AuditOptions:
    tcfg = config.get("thresholds", {})
    thresholds = Thresholds(
        identical=float(getattr(args, "identical_threshold", None) or tcfg.get("identical", 0.999)),
        near=float(getattr(args, "near_threshold", None) or tcfg.get("near", 0.985)),
        divergent=float(getattr(args, "divergent_threshold", None) or tcfg.get("divergent", 0.80)),
    )
    noise = list(config.get("noise_filters", []))
    noise.extend(args.ignore or [])
    return AuditOptions(
        timeout=float(args.timeout or config.get("timeout", 15.0)),
        follow_redirects=not args.no_redirects if args.no_redirects is not None else config.get("follow_redirects", True),
        verify_tls=not args.insecure if args.insecure is not None else config.get("verify_tls", True),
        noise_filters=noise,
        thresholds=thresholds,
    )


def _resolve_matrix(args: argparse.Namespace, config: dict):
    custom: Dict[str, Identity] = {}
    custom_path = args.custom or config.get("custom_identities_file")
    if custom_path:
        custom.update(load_custom_identities(custom_path))
    if "custom_identities" in config:  # inline identities block
        import json, tempfile, os
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(config["custom_identities"], fh)
            tmp = fh.name
        try:
            custom.update(load_custom_identities(tmp))
        finally:
            os.unlink(tmp)
    keys = args.identity or config.get("identities")
    identities = resolve_identities(keys, custom)
    baseline = args.baseline or config.get("baseline", "chrome")
    return identities, baseline, custom


def _emit(text: str, output: Optional[str]) -> None:
    if output and output != "-":
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + ("" if text.endswith("\n") else "\n"))


def _exit_code(report: AuditReport, fail_under: float) -> int:
    if report.overall == "fail":
        return EXIT_PARITY_FAIL
    if report.overall == "incomplete":
        return EXIT_TOOL_ERROR
    if report.minimum_similarity() < fail_under:
        return EXIT_PARITY_FAIL
    return EXIT_OK


def _batch_html(reports: Sequence[AuditReport]) -> str:
    rows = []
    for r in reports:
        rows.append(
            f'<tr><td><a href="#{r.url}">{r.url}</a></td><td>{r.overall}</td>'
            f'<td>{r.minimum_similarity():.3f}</td><td>{len(r.snapshots)}</td></tr>'
        )
    sections = []
    for r in reports:
        sections.append(f'<section id="{r.url}">{render_html(r)}</section>')
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>ParityProbe batch</title></head>"
        "<body><h1>Batch summary</h1><table border=1 cellspacing=0 cellpadding=6>"
        "<tr><th>URL</th><th>Overall</th><th>Min sim</th><th>Identities</th></tr>"
        + "".join(rows) + "</table><hr>" + "".join(sections) + "</body></html>"
    )


def cmd_audit(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    options = _build_options(args, config)
    identities, baseline, _ = _resolve_matrix(args, config)
    fail_under = float(args.fail_under if args.fail_under is not None else config.get("fail_under", 0.80))
    report = audit_url(args.url, identities, baseline_key=baseline, options=options)
    fmt = (args.format or config.get("format", "text")).lower()
    if fmt == "json":
        _emit(render_json(report), args.output)
    elif fmt == "html":
        _emit(render_html(report), args.output)
    else:
        _emit(render_text(report, color=sys.stdout.isatty()), args.output)
    return _exit_code(report, fail_under)


def cmd_batch(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    options = _build_options(args, config)
    identities, baseline, _ = _resolve_matrix(args, config)
    fail_under = float(args.fail_under if args.fail_under is not None else config.get("fail_under", 0.80))
    urls = _read_urls(args.url_file)
    if not urls:
        print("error: URL list is empty", file=sys.stderr)
        return EXIT_TOOL_ERROR
    reports = audit_many(urls, identities, baseline_key=baseline, options=options)
    fmt = (args.format or config.get("format", "text")).lower()
    if fmt == "json":
        import json
        _emit(json.dumps([r.as_dict() for r in reports], ensure_ascii=False, indent=2), args.output)
    elif fmt == "html":
        _emit(_batch_html(reports), args.output)
    else:
        lines = [f"{'URL':<48} {'OVERALL':<10} {'MIN_SIM':<8} WORST"]
        lines.append("-" * 88)
        code = EXIT_OK
        for r in reports:
            worst = next((p for p in r.pairs if p.verdict in ("blocked", "divergent", "error")), None)
            lines.append(f"{r.url:<48} {r.overall:<10} {r.minimum_similarity():<8.3f} "
                         f"{(worst.other_key + ':' + worst.verdict) if worst else '-'}")
        _emit("\n".join(lines), args.output)
        code = max(_exit_code(r, fail_under) for r in reports)
        return code
    return max(_exit_code(r, fail_under) for r in reports)


def cmd_identities(args: argparse.Namespace) -> int:
    custom = load_custom_identities(args.custom) if args.custom else {}
    merged = {**preset_identities(), **custom}
    print(f"{'KEY':<16} {'KIND':<11} {'LABEL':<34} USER-AGENT")
    print("-" * 110)
    for key, ident in merged.items():
        print(f"{key:<16} {ident.kind:<11} {ident.label[:33]:<34} {ident.user_agent}")
    print("\nDefault audit matrix: chrome, googlebot, gptbot, claudebot, bytespider, perplexitybot")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parityprobe",
        description="Audit whether a URL serves equal content to human browsers and AI/search crawlers.",
    )
    parser.add_argument("--version", action="version", version=f"parityprobe {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("-i", "--identity", action="append", help="identity key (repeatable; default: built-in matrix)")
        p.add_argument("-b", "--baseline", help="baseline identity key (default: chrome)")
        p.add_argument("-c", "--config", help="JSON config file")
        p.add_argument("--custom", help="JSON file with custom identities")
        p.add_argument("--timeout", type=float, help="per-request timeout seconds")
        p.add_argument("--ignore", action="append", help="noise regex removed before comparison (repeatable)")
        p.add_argument("--no-redirects", action="store_true", default=None, help="do not follow redirects")
        p.add_argument("--insecure", action="store_true", default=None, help="disable TLS verification")
        p.add_argument("--identical-threshold", type=float)
        p.add_argument("--near-threshold", type=float)
        p.add_argument("--divergent-threshold", type=float)
        p.add_argument("--fail-under", type=float, help="exit code 2 when minimum similarity is below this")
        p.add_argument("-f", "--format", choices=["text", "json", "html"], help="report format")
        p.add_argument("-o", "--output", help="write report to file instead of stdout")

    p_audit = sub.add_parser("audit", help="audit a single URL")
    p_audit.add_argument("url")
    add_common(p_audit)
    p_audit.set_defaults(func=cmd_audit)

    p_batch = sub.add_parser("batch", help="audit many URLs from a text file (one URL per line)")
    p_batch.add_argument("url_file")
    add_common(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    p_id = sub.add_parser("identities", help="list built-in and custom client identities")
    p_id.add_argument("--custom", help="also show identities from a JSON file")
    p_id.set_defaults(func=cmd_identities)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return EXIT_TOOL_ERROR
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TOOL_ERROR
