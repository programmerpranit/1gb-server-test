#!/usr/bin/env python3
"""Build the GitHub Pages site: an index of every configuration plus each results/<tag>/report.html.

Usage:
  python3 -I scripts/pages_site.py <out_dir>

Run by .github/workflows/pages.yml on every push to main that touches results/. Reads only committed files:
results/<tag>/capacity.json, bench.json, vus-*/run.json and report.html. Writes <out_dir>/index.html and
<out_dir>/results/<tag>/report.html (same relative path as in the repo).
"""
import html
import json
import shutil
import sys
from pathlib import Path

REPO = "programmerpranit/1gb-server-test"
ROOT = Path(__file__).resolve().parent.parent


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def configurations():
    rows = []
    for tag_dir in sorted((ROOT / "results").iterdir()):
        cap = load(tag_dir / "capacity.json")
        if not tag_dir.is_dir() or cap is None or not (tag_dir / "report.html").exists():
            continue
        bench = load(tag_dir / "bench.json", {})
        dates = [r.get("date", "") for r in (load(p, {}) for p in tag_dir.glob("vus-*/run.json"))]
        at = cap.get("at_capacity") or {}
        rows.append({
            "tag": tag_dir.name,
            "stack": tag_dir.name.split("-v")[0],
            "date": min(d for d in dates if d)[:10] if any(dates) else "",
            "change": bench.get("change", ""),
            "capacity": cap.get("capacity_vus") or 0,
            "rps": at.get("steady_rps"),
            "first_fail": cap.get("first_fail_vus"),
        })
    rows.sort(key=lambda r: (r["date"], r["tag"]))
    return rows


def index_html(rows):
    best = max(rows, key=lambda r: r["capacity"], default=None)
    trs = []
    for r in rows:
        e = html.escape
        cap = f"{r['capacity']:,}" if r["capacity"] else (f"&lt; {r['first_fail']:,}" if r["first_fail"] else "–")
        rps = f"{r['rps']:,.1f}" if r["rps"] else "–"
        ff = f"{r['first_fail']:,}" if r["first_fail"] else "–"
        cls = ' class="best"' if best and r is best else ""
        trs.append(
            f"<tr{cls}><td><a href=\"results/{e(r['tag'])}/report.html\">{e(r['tag'])}</a></td>"
            f"<td>{e(r['stack'])}</td><td class=n>{cap}</td><td class=n>{rps}</td><td class=n>{ff}</td>"
            f"<td>{e(r['change'])}</td><td>{e(r['date'])}</td>"
            f"<td><a href=\"https://github.com/{REPO}/blob/main/results/{e(r['tag'])}/config.md\">analysis</a></td></tr>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>1 GB Server Benchmarks</title>
<style>
:root {{ --bg:#fff; --fg:#1b1f24; --muted:#59636e; --line:#d1d9e0; --accent:#0969da; --best:#dafbe1; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#30363d;
  --accent:#4493f8; --best:#12261e; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
main {{ max-width:1100px; margin:0 auto; }}
h1 {{ font-size:24px; margin:0 0 8px; }}
p {{ color:var(--muted); margin:0 0 16px; }}
a {{ color:var(--accent); }}
.wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ white-space:nowrap; }}
td.n {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }}
tr.best td {{ background:var(--best); }}
</style></head>
<body><main>
<h1>How far can a $6 droplet go?</h1>
<p>The same social-feed API in different stacks on a DigitalOcean $6 droplet (1 vCPU, 1 GB RAM) with Postgres on the
same box, load-tested with k6 from a second droplet in the same VPC (protocol v2). Capacity = highest VU level whose
steady phase passes p50 &lt; 500 ms, p95 &lt; 800 ms, p99 &lt; 1000 ms and &lt; 1 % errors. Each tag changes one
thing from its parent. Highlighted: best capacity so far.
<a href="https://github.com/{REPO}">Source, methodology and raw data</a>.</p>
<div class="wrap"><table>
<thead><tr><th>Configuration (report)</th><th>Stack</th><th>Capacity VUs</th><th>req/s</th><th>First fail</th>
<th>Change</th><th>Date</th><th></th></tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody></table></div>
</main></body></html>
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    rows = configurations()
    for r in rows:
        dest = out / "results" / r["tag"]
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "results" / r["tag"] / "report.html", dest / "report.html")
    (out / "index.html").write_text(index_html(rows))
    (out / ".nojekyll").write_text("")
    print(f"{len(rows)} configurations -> {out}")


if __name__ == "__main__":
    main()
