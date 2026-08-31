"""Text / JSON / self-contained HTML report renderers."""
from __future__ import annotations

import html as _html
import json
from typing import List

from .audit import AuditReport

__all__ = ["render_json", "render_text", "render_html"]

_VERDICT_COLOR = {
    "pass": 32, "identical": 32, "near-identical": 32,
    "review": 33, "drift": 33, "redirected": 33,
    "fail": 31, "blocked": 31, "divergent": 31, "soft-blocked": 31,
    "incomplete": 35, "error": 35,
}
_BADGE = {
    "pass": "PASS", "review": "REVIEW", "fail": "FAIL", "incomplete": "INCOMPLETE",
}


def render_json(report: AuditReport, indent: int = 2) -> str:
    return json.dumps(report.as_dict(), ensure_ascii=False, indent=indent, sort_keys=False)


def _c(text: str, code: int, enable: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enable else str(text)


def _row(cells, widths):
    return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))


def render_text(report: AuditReport, color: bool = True) -> str:
    lines: List[str] = []
    badge = _BADGE.get(report.overall, report.overall.upper())
    code = _VERDICT_COLOR.get(report.overall, 0)
    lines.append(f"ParityProbe audit · {report.url}")
    lines.append("=" * max(24, len(report.url) + 22))
    lines.append(f"Overall: {_c(badge, code, color)}  baseline={report.baseline_key}  "
                 f"min_similarity={report.minimum_similarity():.3f}  {report.started_at} → {report.finished_at}")
    lines.append("")

    lines.append("Identities observed")
    widths = [max(14, max(len(s.identity_key) for s in report.snapshots) + 1), 11, 8, 10, 9, 9]
    lines.append(_row(["KEY", "KIND", "STATUS", "BYTES", "TOK~", "MS"], widths))
    lines.append(_row(["-" * (w - 1) for w in widths], widths))
    for s in report.snapshots:
        status = str(s.fetch.status) if not s.fetch.error else "ERR"
        c = 32 if s.fetch.ok else (31 if s.fetch.error or s.fetch.status >= 400 else 33)
        lines.append(_row([
            s.identity_key,
            s.kind,
            _c(status, c, color),
            f"{s.fetch.byte_size:,}",
            f"{s.visible_cost.estimated_tokens:,}",
            f"{s.fetch.elapsed_ms:.0f}",
        ], widths))
    lines.append("")

    lines.append("Comparison against baseline (visible-text similarity)")
    if not report.pairs:
        lines.append("  (only the baseline identity was requested)")
    pw = [max(14, max(len(p.other_key) for p in report.pairs) + 1) if report.pairs else 14, 14, 8, 8, 12]
    lines.append(_row(["IDENTITY", "VERDICT", "SIM", "JACC", "+/-LINES"], pw))
    lines.append(_row(["-" * (w - 1) for w in pw], pw))
    for p in report.pairs:
        vc = _VERDICT_COLOR.get(p.verdict, 0)
        lines.append(_row([
            p.other_key,
            _c(p.verdict, vc, color),
            f"{p.visible_similarity:.3f}",
            f"{p.jaccard:.3f}",
            f"+{p.added_lines}/-{p.removed_lines}",
        ], pw))
        for reason in p.reasons:
            lines.append(f"    · {reason}")
    lines.append("")

    if report.hidden_findings:
        lines.append("Identity-specific hidden / machine-directed content")
        for f in report.hidden_findings:
            snippet = " ".join(f["text"].split())[:160]
            lines.append(f"  [{f['identity']}] ({f['reason']}) {snippet}")
        lines.append("")

    machine = []
    for s in report.snapshots:
        for mf in (s.doc.machine_findings if s.doc else []):
            machine.append((s.identity_key, mf.location, mf.snippet))
    if machine:
        lines.append("Machine-addressed phrases detected")
        for key, loc, snip in machine:
            lines.append(f"  [{key}/{loc}] {' '.join(snip.split())[:160]}")
        lines.append("")

    lines.append(f"Notes: {'; '.join(report.overall_notes) if report.overall_notes else '-'}")
    return "\n".join(lines)


def _esc(text) -> str:
    return _html.escape(str(text), quote=True)


def _badge(verdict: str) -> str:
    return f'<span class="badge b-{_html.escape(verdict)}">{_html.escape(verdict)}</span>'


def render_html(report: AuditReport) -> str:
    d = report.as_dict()
    ident_rows = []
    for s in d["identities"]:
        cost = s["visible_cost"]
        status_cls = "ok" if s["ok"] else ("err" if s["error"] or s["status"] >= 400 else "warn")
        hidden = len(s["hidden_blocks"])
        ident_rows.append(
            f'<tr><td class="mono">{_esc(s["key"])}</td><td>{_esc(s["kind"])}</td>'
            f'<td class="{status_cls}">{s["status"] or "ERR"}</td>'
            f'<td class="num">{s["bytes"]:,}</td>'
            f'<td class="num">{cost["estimated_tokens"]:,}</td>'
            f'<td class="num">{s["elapsed_ms"]:.0f}</td>'
            f'<td class="num">{hidden}</td></tr>'
        )

    pair_sections = []
    for i, p in enumerate(d["comparisons"]):
        diff_html = "\n".join(
            f'<span class="diff-add">{_esc(l)}</span>' if l.startswith("+") and not l.startswith("+++")
            else f'<span class="diff-del">{_esc(l)}</span>' if l.startswith("-") and not l.startswith("---")
            else f'<span class="diff-meta">{_esc(l)}</span>' if l.startswith(("+++", "---", "@@"))
            else _esc(l)
            for l in p["diff_preview"][:200]
        )
        reasons = "".join(f"<li>{_esc(r)}</li>" for r in p["reasons"])
        headers = "".join(
            f'<tr><td class="mono">{_esc(k)}</td><td>{_esc(v[0]) or "—"}</td><td>{_esc(v[1]) or "—"}</td></tr>'
            for k, v in p["changed_headers"].items()
        ) or '<tr><td colspan="3" class="muted">No negotiated-header differences</td></tr>'
        pair_sections.append(f"""
        <details {"open" if i == 0 else ""} class="pair v-{_esc(p['verdict'])}">
          <summary><span class="mono">{_esc(p['identity'])}</span> {_badge(p['verdict'])}
            <span class="muted">sim {p['visible_similarity']:.3f} · jaccard {p['token_jaccard']:.3f} · +{p['line_changes']['added']}/-{p['line_changes']['removed']} lines</span>
          </summary>
          <ul class="reasons">{reasons}</ul>
          <h4>Negotiated-header differences</h4>
          <table class="sub"><thead><tr><th>Header</th><th>Baseline</th><th>Identity</th></tr></thead><tbody>{headers}</tbody></table>
          <h4>Visible-text diff (capped preview)</h4>
          <pre class="diff">{diff_html or '<span class="muted">no textual differences</span>'}</pre>
        </details>""")

    hidden_items = "".join(
        f'<li><span class="mono">[{_esc(f["identity"])}]</span> '
        f'<span class="tag">{_esc(f["reason"])}</span> {_esc(f["text"])}</li>'
        for f in d["hidden_findings"]
    ) or '<li class="muted">No identity-specific hidden content found.</li>'

    cards = "".join(
        f'<div class="card"><div class="card-k">{_esc(s.identity_key)}</div>'
        f'<div class="card-v">{s.fetch.status if not s.fetch.error else "ERR"}</div>'
        f'<div class="card-s">{_esc(s.kind)}</div></div>'
        for s in report.snapshots
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ParityProbe · {_esc(report.url)}</title>
<style>
  :root {{
    --bg:#0f1720; --panel:#16212e; --line:#263545; --text:#e6edf3; --muted:#8ba0b4;
    --ok:#2ea043; --warn:#d29922; --err:#e5534b; --accent:#2dd4bf;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:32px 24px 64px; }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  h2 {{ font-size:16px; margin:28px 0 10px; border-left:3px solid var(--accent); padding-left:10px; }}
  h4 {{ font-size:13px; color:var(--muted); margin:14px 0 6px; }}
  .muted {{ color:var(--muted); }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  a {{ color:var(--accent); }}
  .hero {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px 20px; }}
  .hero .url {{ word-break:break-all; color:var(--accent); }}
  .meta {{ display:flex; flex-wrap:wrap; gap:18px; margin-top:10px; color:var(--muted); font-size:13px; }}
  .badge {{ display:inline-block; padding:1px 9px; border-radius:999px; font-size:12px; font-weight:600;
    text-transform:uppercase; letter-spacing:.04em; }}
  .b-pass,.b-identical,.b-near-identical {{ background:rgba(46,160,67,.18); color:#56d364; }}
  .b-review,.b-drift,.b-redirected {{ background:rgba(210,153,34,.18); color:#e3b341; }}
  .b-fail,.b-blocked,.b-divergent {{ background:rgba(229,83,75,.18); color:#f85149; }}
  .b-incomplete,.b-error {{ background:rgba(163,113,247,.18); color:#bc8cff; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:10px; margin-top:12px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:10px 12px; }}
  .card-k {{ font-weight:600; }} .card-v {{ font-size:20px; font-weight:700; margin:2px 0; }} .card-s {{ color:var(--muted); font-size:12px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
  th {{ background:#1b2836; color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
  tr:last-child td {{ border-bottom:none; }}
  td.ok {{ color:#56d364; font-weight:600; }} td.warn {{ color:#e3b341; font-weight:600; }} td.err {{ color:#f85149; font-weight:600; }}
  details.pair {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; margin:10px 0; padding:4px 14px; }}
  details.pair summary {{ cursor:pointer; padding:10px 0; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
  .reasons {{ margin:6px 0; padding-left:20px; color:var(--muted); }}
  table.sub {{ border-radius:6px; font-size:13px; }}
  pre.diff {{ background:#0b1219; border:1px solid var(--line); border-radius:8px; padding:12px; overflow:auto;
    max-height:420px; font:12px/1.5 ui-monospace,Menlo,Consolas,monospace; white-space:pre-wrap; }}
  .diff-add {{ color:#56d364; display:block; }} .diff-del {{ color:#f85149; display:block; }}
  .diff-meta {{ color:var(--muted); display:block; }}
  .tag {{ display:inline-block; background:#1b2836; border:1px solid var(--line); border-radius:6px;
    padding:0 6px; font-size:12px; color:var(--accent); }}
  ul.findings {{ padding-left:18px; }} ul.findings li {{ margin:6px 0; }}
  footer {{ margin-top:36px; color:var(--muted); font-size:12px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>ParityProbe Audit {_badge(report.overall)}</h1>
    <div class="url mono">{_esc(report.url)}</div>
    <div class="meta">
      <span>baseline: <b class="mono">{_esc(report.baseline_key)}</b></span>
      <span>min visible similarity: <b>{report.minimum_similarity():.3f}</b></span>
      <span>started: {_esc(report.started_at)}</span>
      <span>finished: {_esc(report.finished_at)}</span>
    </div>
    <div class="cards">{cards}</div>
  </div>

  <h2>Identities observed</h2>
  <table><thead><tr><th>Key</th><th>Kind</th><th>Status</th><th class="num">Bytes</th>
    <th class="num">Tokens~</th><th class="num">ms</th><th class="num">Hidden blocks</th></tr></thead>
  <tbody>{''.join(ident_rows)}</tbody></table>

  <h2>Pairwise comparison vs baseline</h2>
  {''.join(pair_sections)}

  <h2>Identity-specific hidden / machine-directed content</h2>
  <ul class="findings">{hidden_items}</ul>

  <footer>Generated by ParityProbe · fully offline, single-file report · token counts are documented approximations, not vendor tokenizer output</footer>
</div>
</body>
</html>
"""
