#!/usr/bin/env python3
"""Build an HTML report for one tag: results/<tag>/report.html

Usage: python3 -I scripts/report_html.py results/<tag> [--fragment OUT]
  --fragment OUT  also write the page without the <html>/<head>/<body> wrapper (for publishing as an Artifact)

Inputs (per VU level in results/<tag>/vus-<n>/): summary.json, k6_report.html (k6 web-dashboard export, decoded
for its 2-second snapshots), server_metrics.csv, loadgen_metrics.csv; plus results/<tag>/config.md and capacity.json.
Charts use Chart.js from cdnjs; everything else is inline.
"""
import argparse
import base64
import csv
import glob
import gzip
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

TREND_ORDER = ["avg", "max", "med", "min", "p90", "p95", "p99"]  # k6 dashboard export: stats sorted by name


# ---------------------------------------------------------------- data loading

def load_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def read_csv(path):
    try:
        with open(path) as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def k6_timeseries(report_path):
    """Decode the k6 dashboard export: NDJSON events, gzip+base64 in <script id="data">.
    Snapshot arrays follow the registered metric names in alphabetical order."""
    try:
        text = open(report_path).read()
    except OSError:
        return None
    m = re.search(r'<script[^>]*id="data"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return None
    events = [json.loads(l) for l in gzip.decompress(base64.b64decode(m.group(1).strip())).decode().split("\n")
              if l.strip()]
    names, start_ms, rows = [], None, []
    for ev in events:
        if ev["event"] == "metric":
            names += list(ev["data"].keys())
        elif ev["event"] == "start":
            start_ms = ev["data"][0][0]
        elif ev["event"] == "snapshot":
            snap = dict(zip(sorted(names), ev["data"]))
            rows.append(snap)
    if not rows:
        return None
    start_ms = start_ms or rows[0]["time"][0]

    def trend(snap, metric, stat):
        v = snap.get(metric) or []
        return v[TREND_ORDER.index(stat)] if len(v) == 7 else None

    out = {k: [] for k in ("t", "vus", "rps", "failed_rps", "p50", "p95", "p99", "srv_p95", "conn_p95", "db_p95")}
    for snap in rows:
        t = (snap["time"][0] - start_ms) / 1000
        reqs = snap.get("http_reqs") or []
        rps = reqs[1] if len(reqs) == 2 else 0
        failed = (snap.get("http_req_failed") or [0])[0] if snap.get("http_req_failed") else 0
        out["t"].append(round(t, 1))
        out["vus"].append((snap.get("vus") or [None])[0])
        out["rps"].append(round(rps, 2))
        out["failed_rps"].append(round(rps * failed, 2))
        out["p50"].append(trend(snap, "http_req_duration", "med"))
        out["p95"].append(trend(snap, "http_req_duration", "p95"))
        out["p99"].append(trend(snap, "http_req_duration", "p99"))
        out["srv_p95"].append(trend(snap, "server_total", "p95"))
        out["conn_p95"].append(trend(snap, "server_conn", "p95"))
        out["db_p95"].append(trend(snap, "server_db", "p95"))
    return {"start_ms": start_ms, **out}


def server_timeseries(path, start_s):
    rows = read_csv(path)
    out = {k: [] for k in ("t", "cpu", "app_cpu", "pg_cpu", "mem_used", "conns")}
    for r in rows:
        try:
            t = float(r["ts"]) - start_s
        except (KeyError, ValueError):
            continue
        out["t"].append(round(t, 1))
        out["cpu"].append(float(r["cpu_total_pct"]))
        out["app_cpu"].append(float(r["app_cpu_pct"]))
        out["pg_cpu"].append(float(r["pg_cpu_pct"]))
        out["mem_used"].append(float(r["mem_used_mb"]))
        out["conns"].append(float(r["app_conns"]))
    return out


def loadgen_timeseries(path, start_s):
    rows = read_csv(path)
    out = {"t": [], "cpu": []}
    for r in rows:
        try:
            out["t"].append(round(float(r["ts"]) - start_s, 1))
            out["cpu"].append(float(r["lg_cpu_pct"]))
        except (KeyError, ValueError):
            continue
    return out


def collect(tag_dir):
    levels = []
    for d in glob.glob(os.path.join(tag_dir, "vus-*")):
        s = load_json(os.path.join(d, "summary.json"))
        if not s:
            continue
        start_ms = (load_json(os.path.join(d, "k6_start.json"), {}) or {}).get("started_at_ms")
        k6 = k6_timeseries(os.path.join(d, "k6_report.html"))
        start_s = (start_ms or (k6 or {}).get("start_ms") or s["k6_started_at"] * 1000) / 1000
        st, srv = s.get("server_timing_ms", {}), s.get("server", {})
        levels.append({
            "vus": s["vus"], "pass": s["pass"], "fail_reasons": s["fail_reasons"],
            "rps": s["steady_rps"], "rpm": s["steady_rpm"], "total": s["total_requests"],
            "err": s["error_rate_pct"],
            "lat": {k.replace("(", "").replace(")", ""): v for k, v in s["steady_latency_ms"].items()},
            "srv": {part: {k.replace("(", "").replace(")", ""): v for k, v in (st.get(part) or {}).items()}
                    for part in ("total", "conn", "db", "app")},
            "outside": s.get("outside_ms", {}),
            "cpu": srv.get("cpu_total_pct_avg_steady"), "app_cpu": srv.get("app_cpu_pct_avg_steady"),
            "pg_cpu": srv.get("pg_cpu_pct_avg_steady"), "steal": srv.get("cpu_steal_pct_avg_steady"),
            "mem_used": srv.get("mem_used_mb_peak"), "app_mb": srv.get("app_pss_mb_peak"),
            "pg_mb": srv.get("pg_pss_mb_peak"), "lg_cpu": (s.get("loadgen_stats") or {}).get("lg_cpu_pct_peak"),
            "endpoints": {k: [v, (s.get("server_total_p95_by_endpoint_ms") or {}).get(k)]
                          for k, v in s["per_endpoint_p95_ms"].items()},
            "ramp_s": s["ramp_s"], "hold_s": s["hold_s"],
            "k6": k6,
            "server": server_timeseries(os.path.join(d, "server_metrics.csv"), start_s),
            "loadgen": loadgen_timeseries(os.path.join(d, "loadgen_metrics.csv"), start_s),
            "meta": {k: s.get(k) for k in ("date", "git_sha", "loadgen", "k6_version", "stack")},
            "bench": s.get("bench") or {}, "env": s.get("server_env") or {}, "criteria": s.get("criteria") or {},
        })
    levels.sort(key=lambda l: l["vus"])
    return levels


# ---------------------------------------------------------------- markdown (the subset config.md uses)

def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])_([^_]+)_(?![\w*])", r"<em>\1</em>", t)
    return t


def markdown(md):
    lines, out, i = md.strip("\n").split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>"); i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[2:]]
            out.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                                                          for r in body) + "</tbody></table></div>")
        elif re.match(r"^- ", line):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or (lines[i].startswith("  ") and items)):
                if lines[i].startswith("- "):
                    items.append(lines[i][2:].strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(it)}</li>" for it in items) + "</ul>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("- ", "|", "### ")):
                para.append(lines[i].strip()); i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def sections(md_path):
    try:
        text = open(md_path).read()
    except OSError:
        return {}
    parts, current = {}, None
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line[3:].strip(); parts[current] = []
        elif current:
            parts[current].append(line)
    return {k: "\n".join(v) for k, v in parts.items()}


# ---------------------------------------------------------------- page

def fmt(v, d=0):
    if v is None:
        return "–"
    return f"{v:,.{d}f}"


def build(tag_dir):
    tag = os.path.basename(os.path.normpath(tag_dir))
    levels = collect(tag_dir)
    if not levels:
        sys.exit(f"no summarised runs in {tag_dir}")
    cap = load_json(os.path.join(tag_dir, "capacity.json"), {}) or {}
    sec = sections(os.path.join(tag_dir, "config.md"))
    best = next((l for l in reversed(levels) if l["pass"]), None)
    ref = best or levels[0]
    first_fail = cap.get("first_fail_vus")
    crit = ref["criteria"] or {"p50": 500, "p95": 800, "p99": 1000, "error_pct": 1}
    bench, env, meta = ref["bench"], ref["env"], ref["meta"]
    ceiling = max(l["rps"] for l in levels)
    srv = ref["srv"]
    conn_share = (srv["conn"]["med"] / srv["total"]["med"] * 100) if srv["total"].get("med") else None

    rows = []
    for l in levels:
        chip = '<span class="chip pass">Pass</span>' if l["pass"] else '<span class="chip fail">Fail</span>'
        why = "" if l["pass"] else f'<span class="why">{html.escape(", ".join(l["fail_reasons"]))}</span>'
        cell = lambda v, lim: f'<td class="num{" over" if v is not None and v >= lim else ""}">{fmt(v)}</td>'
        rows.append(
            f'<tr{" class=best" if l is best else ""}><td class="num strong">{l["vus"]:,}</td><td>{chip}{why}</td>'
            f'<td class="num">{fmt(l["rps"], 1)}</td>'
            + cell(l["lat"].get("med"), crit["p50"]) + cell(l["lat"].get("p95"), crit["p95"])
            + cell(l["lat"].get("p99"), crit["p99"])
            + f'<td class="num{" over" if l["err"] >= crit["error_pct"] else ""}">{fmt(l["err"], 2)}</td>'
            f'<td class="num">{fmt(l["srv"]["total"].get("med"))} / {fmt(l["srv"]["total"].get("p95"))}</td>'
            f'<td class="num">{fmt(l["srv"]["conn"].get("med"))} / {fmt(l["srv"]["conn"].get("p95"))}</td>'
            f'<td class="num">{fmt(l["cpu"])} <span class="sub">({fmt(l["app_cpu"])} / {fmt(l["pg_cpu"])})</span></td>'
            f'<td class="num">{fmt(l["mem_used"])}</td><td class="num">{fmt(l["lg_cpu"])}</td></tr>')

    def md_section(name, anchor):
        body = sec.get(name)
        return f'<section id="{anchor}"><h2>{html.escape(name)}</h2>{markdown(body)}</section>' if body else ""

    data = {"levels": levels, "criteria": crit, "best": best["vus"] if best else None}
    cap_text = f'{best["vus"]:,} VUs' if best else f"< {levels[0]['vus']:,} VUs"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = f"{tag} report"
    data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

    body = f"""<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>{CSS}</style>
<div class="page">
<header class="masthead">
  <p class="eyebrow">1 GB server test · protocol v2 · {html.escape(env.get("os", "Ubuntu"))} on a $6 droplet (1 vCPU / 1 GB)</p>
  <h1>{html.escape(tag)}</h1>
  <p class="meta">{html.escape(bench.get("framework", meta.get("stack") or ""))} · {html.escape(bench.get("db_driver", ""))}
    · pool: {html.escape(bench.get("db_pool", "–"))} · Node {html.escape(env.get("node", "–"))} · Postgres {html.escape(env.get("postgres", "–"))}
    · load from <code>{html.escape(meta.get("loadgen") or "")}</code> · app {html.escape(meta.get("git_sha") or "")}</p>
  <div class="verdict">
    <div class="v-main"><span class="v-label">Capacity</span><span class="v-value">{cap_text}</span>
      <span class="v-sub">{fmt(ref["rps"], 1) + " req/s steady" if best else "no level passed"}</span></div>
    <div><span class="v-label">First failing level</span><span class="v-value small">{f"{first_fail:,} VUs" if first_fail else "none tested"}</span></div>
    <div><span class="v-label">Highest throughput seen</span><span class="v-value small">{fmt(ceiling, 1)} req/s</span></div>
    <div><span class="v-label">Pass rule</span><span class="v-rule">p50 &lt; {crit["p50"]:g} · p95 &lt; {crit["p95"]:g} · p99 &lt; {crit["p99"]:g} ms<br>errors &lt; {crit["error_pct"]:g} %</span></div>
  </div>
</header>

<section class="kpis" aria-label="At capacity">
  <div class="kpi"><span>Steady throughput</span><b>{fmt(ref["rps"], 1)}</b><em>req/s · {fmt(ref["rpm"])} req/min</em></div>
  <div class="kpi"><span>Client p95 / p99</span><b>{fmt(ref["lat"].get("p95"))} / {fmt(ref["lat"].get("p99"))}</b><em>ms, steady phase</em></div>
  <div class="kpi"><span>Server time p50</span><b>{fmt(srv["total"].get("med"), 1)}</b><em>ms inside the app</em></div>
  <div class="kpi"><span>Spent getting a connection</span><b>{fmt(conn_share)} %</b><em>of server p50 ({fmt(srv["conn"].get("med"), 1)} ms)</em></div>
  <div class="kpi"><span>CPU (1 vCPU)</span><b>{fmt(ref["cpu"])} %</b><em>Node {fmt(ref["app_cpu"])} · Postgres {fmt(ref["pg_cpu"])}</em></div>
  <div class="kpi"><span>Memory used</span><b>{fmt(ref["mem_used"])} MB</b><em>of 961 MB · Node {fmt(ref["app_mb"])} · PG {fmt(ref["pg_mb"])}</em></div>
</section>

{md_section("Summary", "summary")}

<section id="levels">
  <h2>Levels tested</h2>
  <p class="note">Latency is the client-observed steady phase (60 s hold). Red values miss the pass rule. Server and conn come from the app's <code>Server-Timing</code> header, p50 / p95 in ms.</p>
  <div class="table-wrap"><table class="levels">
    <thead><tr><th>VUs</th><th>Result</th><th>req/s</th><th>p50</th><th>p95</th><th>p99</th><th>Errors %</th><th>Server</th><th>Conn</th><th>CPU % (Node / PG)</th><th>Used MB</th><th>Load gen CPU %</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>

<section id="across">
  <h2>Across levels</h2>
  <div class="grid2">
    <figure><figcaption>Client latency vs. users <span>steady phase, ms; dashed = limits</span></figcaption><div class="chart"><canvas id="c-lat"></canvas></div></figure>
    <figure><figcaption>Where server time goes <span>p50 per request, ms</span></figcaption><div class="chart"><canvas id="c-split"></canvas></div></figure>
  </div>
</section>

<section id="timeline">
  <h2>During the run</h2>
  <div class="picker" role="tablist" aria-label="VU level">{"".join(f'<button role="tab" type="button" data-vus="{l["vus"]}" id="tab-{l["vus"]}">{l["vus"]:,} VUs</button>' for l in levels)}</div>
  <p class="note">From k6's 2-second snapshots and the 1-second server samples, aligned on the k6 start. The shaded band is the 60 s ramp; the hold phase follows.</p>
  <div class="grid2">
    <figure><figcaption>Load <span>active users, req/s, failed req/s</span></figcaption><div class="chart"><canvas id="c-load"></canvas></div></figure>
    <figure><figcaption>Latency over time <span>2 s windows, ms</span></figcaption><div class="chart"><canvas id="c-time"></canvas></div></figure>
    <figure><figcaption>Target droplet <span>CPU % of 1 vCPU, memory used MB</span></figcaption><div class="chart"><canvas id="c-cpu"></canvas></div></figure>
    <figure><figcaption>p95 by endpoint <span>client vs. server, ms, whole run</span></figcaption><div class="chart"><canvas id="c-ep"></canvas></div></figure>
  </div>
</section>

{md_section("What changed vs. the previous tag", "changed")}
{md_section("Full configuration", "config")}
{md_section("Observations", "observations")}
{md_section("Next idea", "next")}

<footer>
  <p>Generated {generated} by <code>scripts/report_html.py</code> from <code>results/{html.escape(tag)}/</code>. Raw data per level: <code>summary.json</code>, <code>k6_summary.json</code>, <code>k6_report.html</code> (full k6 dashboard), <code>server_metrics.csv</code>, <code>loadgen_metrics.csv</code>.</p>
</footer>
</div>
<script type="application/json" id="report-data">{data_json}</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>{JS}</script>
"""
    return title, body


CSS = r"""
/* Layout: one reading column (max 1180px) with a measurement-sheet masthead; charts in a 2-up grid that stacks. */
:root{
  --bg:#f4f6f8; --surface:#ffffff; --ink:#15202b; --muted:#5b6876; --line:#d9e0e7; --accent:#2457c5;
  --pass:#1d7a46; --pass-bg:#e3f3ea; --fail:#b42318; --fail-bg:#fde8e6;
  --s-client:#2457c5; --s-p99:#7a8aa3; --s-srv:#0f8b8d; --s-conn:#c4760f; --s-db:#0f8b8d; --s-app:#8b5cf6;
  --s-cpu:#15202b; --s-node:#2457c5; --s-pg:#c4760f; --s-mem:#0f8b8d; --band:rgba(36,87,197,.07);
  --f-display:"Archivo","Helvetica Neue",Arial,sans-serif;
  --f-body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f1419; --surface:#161d24; --ink:#e3e9ef; --muted:#93a1b0; --line:#2a3440; --accent:#7aa2ff;
  --pass:#5cc98a; --pass-bg:#173326; --fail:#ff8a7a; --fail-bg:#3a1d1a;
  --s-client:#7aa2ff; --s-p99:#8d9bb0; --s-srv:#3cc7c4; --s-conn:#f0a640; --s-db:#3cc7c4; --s-app:#b69bff;
  --s-cpu:#e3e9ef; --s-node:#7aa2ff; --s-pg:#f0a640; --s-mem:#3cc7c4; --band:rgba(122,162,255,.09); color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f1419; --surface:#161d24; --ink:#e3e9ef; --muted:#93a1b0; --line:#2a3440; --accent:#7aa2ff;
  --pass:#5cc98a; --pass-bg:#173326; --fail:#ff8a7a; --fail-bg:#3a1d1a;
  --s-client:#7aa2ff; --s-p99:#8d9bb0; --s-srv:#3cc7c4; --s-conn:#f0a640; --s-db:#3cc7c4; --s-app:#b69bff;
  --s-cpu:#e3e9ef; --s-node:#7aa2ff; --s-pg:#f0a640; --s-mem:#3cc7c4; --band:rgba(122,162,255,.09); color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg); color:var(--ink); font:15px/1.6 var(--f-body); margin:0}
.page{max-width:1180px; margin:0 auto; padding-inline:clamp(16px,4vw,40px); padding-block:28px 56px; display:grid; gap:40px}
h1,h2,h3{font-family:var(--f-display); text-wrap:balance; line-height:1.15; margin:0}
h1{font-size:clamp(28px,4.4vw,44px); font-weight:800; font-stretch:80%; letter-spacing:-.01em; overflow-wrap:anywhere}
h2{font-size:22px; font-weight:700; font-stretch:85%; margin-bottom:14px}
h3{font-size:17px; margin:18px 0 8px}
p,li{max-width:76ch}
code{font-family:var(--f-mono); font-size:.86em; background:color-mix(in srgb,var(--line) 55%,transparent); padding:1px 5px; border-radius:4px}
section{min-width:0}
section ul{padding-left:20px; margin:0; display:grid; gap:8px}
section p{margin:0 0 10px}
.eyebrow{font:500 12px/1.4 var(--f-mono); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:0 0 8px}
.meta{color:var(--muted); margin:10px 0 0; font-size:14px}
.masthead{border-bottom:2px solid var(--ink); padding-bottom:22px}
.verdict{display:grid; grid-template-columns:1.4fr repeat(3,1fr); gap:1px; background:var(--line); border:1px solid var(--line); margin-top:22px}
.verdict>div{background:var(--surface); padding:14px 16px; display:flex; flex-direction:column; gap:2px; min-width:0}
.v-label{font:500 11px/1.3 var(--f-mono); letter-spacing:.06em; text-transform:uppercase; color:var(--muted)}
.v-value{font:800 34px/1.1 var(--f-display); font-stretch:80%; color:var(--accent); font-variant-numeric:tabular-nums}
.v-value.small{font-size:24px; color:var(--ink)}
.v-sub{color:var(--muted); font-size:13px}
.v-rule{font:13px/1.5 var(--f-mono)}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px}
.kpi{background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:12px 14px; display:flex; flex-direction:column; gap:2px}
.kpi span{font:500 11px/1.3 var(--f-mono); letter-spacing:.05em; text-transform:uppercase; color:var(--muted)}
.kpi b{font:700 24px/1.2 var(--f-display); font-stretch:85%; font-variant-numeric:tabular-nums}
.kpi em{font-style:normal; color:var(--muted); font-size:12.5px}
.note{color:var(--muted); font-size:13.5px}
.table-wrap{overflow-x:auto; border:1px solid var(--line); border-radius:6px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:13.5px}
th,td{padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; vertical-align:top}
th{font:500 11px/1.3 var(--f-mono); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); background:color-mix(in srgb,var(--line) 30%,var(--surface))}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:var(--f-mono); font-variant-numeric:tabular-nums}
td.strong{font-weight:500}
td.over{color:var(--fail); font-weight:500}
tr.best td{background:color-mix(in srgb,var(--pass-bg) 60%,transparent)}
.sub{color:var(--muted)}
.chip{display:inline-block; font:500 11px/1 var(--f-mono); letter-spacing:.05em; text-transform:uppercase; padding:4px 7px; border-radius:3px}
.chip.pass{color:var(--pass); background:var(--pass-bg)}
.chip.fail{color:var(--fail); background:var(--fail-bg)}
.why{display:block; color:var(--muted); font-size:12px; margin-top:4px}
.grid2{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px}
figure{margin:0; background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:12px 14px 10px; min-width:0}
figcaption{font:600 14px/1.3 var(--f-body); margin-bottom:8px}
figcaption span{display:block; font:400 12px/1.4 var(--f-mono); color:var(--muted)}
.chart{position:relative; height:280px}
.picker{display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px}
.picker button{font:500 13px/1 var(--f-mono); padding:8px 12px; border-radius:4px; border:1px solid var(--line); background:var(--surface); color:var(--ink); cursor:pointer}
.picker button[aria-selected="true"]{background:var(--accent); border-color:var(--accent); color:var(--surface)}
.picker button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
footer{border-top:1px solid var(--line); padding-top:14px; color:var(--muted); font-size:13px}
@media (max-width:760px){.verdict{grid-template-columns:1fr 1fr}.verdict>div:first-child{grid-column:1/-1}.grid2{grid-template-columns:1fr}.chart{height:240px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important; transition:none!important}}
"""

JS = r"""
(function(){
  const D = JSON.parse(document.getElementById('report-data').textContent);
  const L = D.levels, C = D.criteria;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  let charts = [], current = D.best || L[0].vus;
  try { const saved = localStorage.getItem('report-vus'); if (saved && L.some(l => l.vus == saved)) current = +saved; } catch (e) {}

  const rampBand = {id:'rampBand', beforeDatasetsDraw(chart, args, opts){
    if (opts.until == null) return; const {ctx, chartArea:a, scales:{x}} = chart;
    const x1 = Math.min(x.getPixelForValue(opts.until), a.right);
    ctx.save(); ctx.fillStyle = css('--band'); ctx.fillRect(a.left, a.top, x1 - a.left, a.bottom - a.top); ctx.restore();
  }};

  function base(){
    Chart.defaults.font.family = css('--f-mono').split(',')[0].replace(/"/g,'') || 'monospace';
    Chart.defaults.font.size = 11;
    Chart.defaults.color = css('--muted');
    Chart.defaults.borderColor = css('--line');
    Chart.defaults.animation = matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {duration: 250};
  }
  const line = (label, data, color, extra) => Object.assign({label, data, borderColor: color, backgroundColor: color,
    borderWidth: 1.8, pointRadius: 0, tension: .25, spanGaps: true}, extra || {});
  const xy = (t, v) => t.map((x, i) => ({x, y: v[i]}));
  const opts = (extra) => Object.assign({responsive:true, maintainAspectRatio:false, interaction:{mode:'index', intersect:false},
    plugins:{legend:{position:'bottom', labels:{boxWidth:10, boxHeight:10, usePointStyle:true}}}}, extra || {});

  function across(){
    const vus = L.map(l => l.vus);
    const limit = (v, label) => line(label, vus.map(() => v), css('--fail'), {borderDash:[5,4], borderWidth:1.2, pointRadius:0});
    charts.push(new Chart(document.getElementById('c-lat'), {type:'line', data:{labels: vus.map(v => v + ' VUs'), datasets:[
      line('p50', L.map(l => l.lat.med), css('--s-srv'), {pointRadius:4}),
      line('p95', L.map(l => l.lat.p95), css('--s-client'), {pointRadius:4}),
      line('p99', L.map(l => l.lat.p99), css('--s-p99'), {pointRadius:4}),
      limit(C.p95, 'p95 limit'), limit(C.p99, 'p99 limit')]},
      options: opts({scales:{y:{beginAtZero:true, title:{display:true, text:'ms'}}}})}));
    charts.push(new Chart(document.getElementById('c-split'), {type:'bar', data:{labels: vus.map(v => v + ' VUs'), datasets:[
      {label:'conn (get a DB connection)', data: L.map(l => l.srv.conn.med), backgroundColor: css('--s-conn'), stack:'s'},
      {label:'db (queries)', data: L.map(l => l.srv.db.med), backgroundColor: css('--s-db'), stack:'s'},
      {label:'app (Node work)', data: L.map(l => l.srv.app.med), backgroundColor: css('--s-app'), stack:'s'}]},
      options: opts({scales:{x:{stacked:true}, y:{stacked:true, beginAtZero:true, title:{display:true, text:'ms'}}}})}));
  }

  let perLevel = [];
  function level(vus){
    perLevel.forEach(c => c.destroy()); perLevel = [];
    const l = L.find(x => x.vus == vus); if (!l) return;
    const k = l.k6, s = l.server, ramp = {rampBand:{until: l.ramp_s}};
    const xAxis = {type:'linear', min:0, max: l.ramp_s + l.hold_s + 5, title:{display:true, text:'seconds since k6 start'}, ticks:{stepSize:20}};
    if (k) {
      perLevel.push(new Chart(document.getElementById('c-load'), {type:'line', plugins:[rampBand], data:{datasets:[
        line('active users', xy(k.t, k.vus), css('--s-cpu'), {yAxisID:'y1'}),
        line('req/s', xy(k.t, k.rps), css('--s-client')),
        line('failed req/s', xy(k.t, k.failed_rps), css('--fail'))]},
        options: opts({plugins:{...opts().plugins, ...ramp}, scales:{x:xAxis, y:{beginAtZero:true, title:{display:true, text:'req/s'}},
          y1:{position:'right', beginAtZero:true, grid:{drawOnChartArea:false}, title:{display:true, text:'users'}}}})}));
      perLevel.push(new Chart(document.getElementById('c-time'), {type:'line', plugins:[rampBand], data:{datasets:[
        line('client p95', xy(k.t, k.p95), css('--s-client')),
        line('client p99', xy(k.t, k.p99), css('--s-p99'), {borderDash:[3,3]}),
        line('server total p95', xy(k.t, k.srv_p95), css('--s-srv')),
        line('conn p95', xy(k.t, k.conn_p95), css('--s-conn'))]},
        options: opts({plugins:{...opts().plugins, ...ramp}, scales:{x:xAxis, y:{beginAtZero:true, title:{display:true, text:'ms'}}}})}));
    }
    perLevel.push(new Chart(document.getElementById('c-cpu'), {type:'line', plugins:[rampBand], data:{datasets:[
      line('CPU total', xy(s.t, s.cpu), css('--s-cpu')),
      line('Node', xy(s.t, s.app_cpu), css('--s-node')),
      line('Postgres', xy(s.t, s.pg_cpu), css('--s-pg')),
      line('memory used MB', xy(s.t, s.mem_used), css('--s-mem'), {yAxisID:'y1', borderDash:[4,3]})]},
      options: opts({plugins:{...opts().plugins, ...ramp}, scales:{x:xAxis, y:{min:0, max:100, title:{display:true, text:'CPU %'}},
        y1:{position:'right', min:0, max:1000, grid:{drawOnChartArea:false}, title:{display:true, text:'MB'}}}})}));
    const NAMES = {'GET /posts':'feed', 'GET /posts/:id':'view post', 'GET /users/:id/posts':'user posts',
      'GET /me/posts':'my posts', 'POST /posts':'create post', 'POST /posts/:id/like':'like',
      'DELETE /posts/:id/like':'unlike', 'POST /posts/:id/comments':'comment'};
    const eps = Object.keys(l.endpoints).sort((a, b) => (NAMES[a] || a).localeCompare(NAMES[b] || b));
    perLevel.push(new Chart(document.getElementById('c-ep'), {type:'bar', data:{labels: eps.map(e => NAMES[e] || e), datasets:[
      {label:'client p95', data: eps.map(e => l.endpoints[e][0]), backgroundColor: css('--s-client')},
      {label:'server total p95', data: eps.map(e => l.endpoints[e][1]), backgroundColor: css('--s-srv')}]},
      options: opts({indexAxis:'y', scales:{x:{beginAtZero:true, title:{display:true, text:'ms'}}},
        plugins:{...opts().plugins, tooltip:{callbacks:{title: items => eps[items[0].dataIndex]}}}})}));
    document.querySelectorAll('.picker button').forEach(b => b.setAttribute('aria-selected', b.dataset.vus == vus ? 'true' : 'false'));
  }

  function render(){
    if (!window.Chart) return;
    charts.forEach(c => c.destroy()); charts = [];
    base(); across(); level(current);
  }
  document.querySelectorAll('.picker button').forEach(b => b.addEventListener('click', () => {
    current = +b.dataset.vus; try { localStorage.setItem('report-vus', current); } catch (e) {}
    level(current);
  }));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
  new MutationObserver(render).observe(document.documentElement, {attributes:true, attributeFilter:['data-theme']});
  render();
})();
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag_dir")
    ap.add_argument("--fragment", metavar="OUT")
    a = ap.parse_args()
    title, body = build(a.tag_dir)
    out = os.path.join(a.tag_dir, "report.html")
    with open(out, "w") as fh:
        head, content = body.split('<div class="page">', 1)
        fh.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                 + head + '</head>\n<body>\n<div class="page">' + content + "</body>\n</html>\n")
    if a.fragment:
        with open(a.fragment, "w") as fh:
            fh.write(body)
    print(out)


if __name__ == "__main__":
    main()
