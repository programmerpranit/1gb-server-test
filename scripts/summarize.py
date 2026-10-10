#!/usr/bin/env python3
"""Combine k6_summary.json + server_metrics.csv of one run into summary.json / summary.md,
and upsert the run's row into README.md's results table.

Usage: python3 -I scripts/summarize.py <run_dir> [--readme README.md]
<run_dir> = results/<tag>/vus-<n>/ containing run.json, k6_summary.json, server_metrics.csv
"""
import csv
import json
import os
import sys

README_START = "<!-- RESULTS:START -->"
README_END = "<!-- RESULTS:END -->"
COLUMNS = ["Tag", "Stack", "VUs", "Steady req/s", "Steady req/min", "Total req", "p50 ms", "p90 ms",
           "p95 ms", "p99 ms", "Max ms", "Error %", "App MB (peak)", "PG MB (peak)", "Used MB (peak)",
           "Swap MB", "CPU % (avg steady)", "Steal %", "Load from"]


def metric(k6, name, stat):
    m = k6["metrics"].get(name)
    return None if m is None else m["values"].get(stat)


def fmt(v, digits=1):
    if v is None:
        return "-"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def server_stats(path, steady_from, steady_to):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append({k: float(v) for k, v in r.items()})
            except (TypeError, ValueError):
                continue
    if not rows:
        return {}
    steady = [r for r in rows if steady_from <= r["ts"] <= steady_to] or rows
    avg = lambda key, rs: sum(r[key] for r in rs) / len(rs)
    return {
        "app_pss_mb_peak": max(r["app_pss_mb"] for r in rows),
        "pg_pss_mb_peak": max(r["pg_pss_mb"] for r in rows),
        "mem_used_mb_peak": max(r["mem_used_mb"] for r in rows),
        "mem_avail_mb_min": min(r["mem_avail_mb"] for r in rows),
        "swap_used_mb_peak": max(r["swap_used_mb"] for r in rows),
        "cpu_total_pct_avg_steady": avg("cpu_total_pct", steady),
        "cpu_steal_pct_avg_steady": avg("cpu_steal_pct", steady),
        "app_cpu_pct_avg_steady": avg("app_cpu_pct", steady),
        "pg_cpu_pct_avg_steady": avg("pg_cpu_pct", steady),
        "app_conns_peak": max(r["app_conns"] for r in rows),
        "load1_peak": max(r["load1"] for r in rows),
    }


def summarize(run_dir):
    run = json.load(open(os.path.join(run_dir, "run.json")))
    k6 = json.load(open(os.path.join(run_dir, "k6_summary.json")))

    steady_count = metric(k6, "http_reqs{phase:steady}", "count") or 0
    hold_s = run["hold_s"]
    s = {
        **run,
        "total_requests": metric(k6, "http_reqs", "count"),
        "avg_rps": metric(k6, "http_reqs", "rate"),
        "steady_requests": steady_count,
        "steady_rps": steady_count / hold_s if hold_s else None,
        "steady_rpm": steady_count * 60 / hold_s if hold_s else None,
        "vus_max": metric(k6, "vus_max", "max"),
        "iterations": metric(k6, "iterations", "count"),
        "error_rate_pct": 100 * (metric(k6, "http_req_failed", "rate") or 0),
        "steady_error_rate_pct": 100 * (metric(k6, "http_req_failed{phase:steady}", "rate") or 0),
        "latency_ms": {k: metric(k6, "http_req_duration", k)
                       for k in ("avg", "med", "p(90)", "p(95)", "p(99)", "max")},
        "steady_latency_ms": {k: metric(k6, "http_req_duration{phase:steady}", k)
                              for k in ("avg", "med", "p(90)", "p(95)", "p(99)", "max")},
        "per_endpoint_p95_ms": {
            name.split("name:", 1)[1].rstrip("}"): m["values"].get("p(95)")
            for name, m in k6["metrics"].items() if name.startswith("http_req_duration{name:")
        },
    }
    # Prefer the k6 setup() timestamp; fall back to the wall clock taken before k6 launched.
    # Server samples use the droplet clock — both machines should run NTP.
    started = run["k6_started_at"]
    start_file = os.path.join(run_dir, "k6_start.json")
    if os.path.exists(start_file):
        ms = json.load(open(start_file)).get("started_at_ms")
        if ms:
            started = ms / 1000
    steady_from = started + run["ramp_s"]
    metrics_csv = os.path.join(run_dir, "server_metrics.csv")
    if os.path.exists(metrics_csv):
        s["server"] = server_stats(metrics_csv, steady_from, steady_from + hold_s)

    with open(os.path.join(run_dir, "summary.json"), "w") as fh:
        json.dump(s, fh, indent=2)

    srv = s.get("server", {})
    lat = s["steady_latency_ms"]
    row = [s["tag"], s["stack"], s["vus"], fmt(s["steady_rps"]), fmt(s["steady_rpm"], 0),
           s["total_requests"], fmt(lat["med"]), fmt(lat["p(90)"]), fmt(lat["p(95)"]), fmt(lat["p(99)"]),
           fmt(lat["max"], 0), fmt(s["error_rate_pct"], 2), fmt(srv.get("app_pss_mb_peak"), 0),
           fmt(srv.get("pg_pss_mb_peak"), 0), fmt(srv.get("mem_used_mb_peak"), 0),
           fmt(srv.get("swap_used_mb_peak"), 0), fmt(srv.get("cpu_total_pct_avg_steady")),
           fmt(srv.get("cpu_steal_pct_avg_steady")), s["loadgen"]]
    row = [str(c) for c in row]

    md = [f"# {s['tag']} — {s['vus']} VUs", "",
          "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS), "| " + " | ".join(row) + " |", "",
          "Latency columns are steady-state (hold phase). Error % covers the whole run.", "",
          "## p95 by endpoint (ms, whole run)", ""]
    md += [f"- `{k}`: {fmt(v)}" for k, v in sorted(s["per_endpoint_p95_ms"].items())]
    with open(os.path.join(run_dir, "summary.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    return s, row


def upsert_readme(readme, row):
    text = open(readme).read()
    if README_START not in text or README_END not in text:
        print(f"{readme}: results markers missing, not updated", file=sys.stderr)
        return
    head, rest = text.split(README_START, 1)
    body, tail = rest.split(README_END, 1)
    lines = [l for l in body.strip("\n").split("\n") if l.strip()]
    header = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    data = [l for l in lines[2:]] if len(lines) >= 2 else []
    key = f"| {row[0]} | {row[1]} | {row[2]} |"
    data = [l for l in data if not l.startswith(key)]
    data.append("| " + " | ".join(row) + " |")
    out = head + README_START + "\n" + "\n".join(header + data) + "\n" + README_END + tail
    with open(readme, "w") as fh:
        fh.write(out)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    readme = None
    if "--readme" in args:
        i = args.index("--readme")
        readme = args[i + 1]
        del args[i:i + 2]
    s, row = summarize(args[0])
    if readme:
        upsert_readme(readme, row)
    print("| " + " | ".join(row) + " |")
    print(f"error_rate_pct={s['error_rate_pct']:.2f}")


if __name__ == "__main__":
    main()
