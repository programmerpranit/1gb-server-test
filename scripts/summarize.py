#!/usr/bin/env python3
"""Summarise test runs.

Per run:
  python3 -I scripts/summarize.py <run_dir> [criteria] [--readme README.md] [--csv results/results.csv]
  <run_dir> = results/<tag>/vus-<n>/ with run.json, k6_summary.json, server_metrics.csv, server_env.txt, bench.json
  Writes summary.json / summary.md, judges pass/fail, upserts the run into README "All runs" and the CSV.
  Prints the README row, then `pass=0|1`, `fail_reasons=...`, `error_rate_pct=...`.

Per tag (after a search):
  python3 -I scripts/summarize.py --capacity results/<tag> [criteria] [--readme README.md]
  Writes results/<tag>/capacity.json and upserts the README "Capacity" row.

Criteria (defaults): --p50 500 --p95 800 --p99 1000 --error-pct 1
  Pass = steady-phase p50/p95/p99 strictly below the limits AND whole-run error % strictly below the limit.
"""
import argparse
import csv
import glob
import json
import os

RUNS_START, RUNS_END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"
CAP_START, CAP_END = "<!-- CAPACITY:START -->", "<!-- CAPACITY:END -->"
REPO = "https://github.com/programmerpranit/1gb-server-test"

RUN_COLUMNS = ["Tag", "Stack", "VUs", "Pass", "Steady req/s", "Steady req/min", "Total req", "p50 ms", "p90 ms",
               "p95 ms", "p99 ms", "Max ms", "Error %", "App MB (peak)", "PG MB (peak)", "Used MB (peak)",
               "Swap MB", "CPU % (avg steady)", "Steal %", "Load from"]
CAP_COLUMNS = ["Tag", "Stack", "What changed", "Capacity (VUs)", "First fail (VUs)", "Steady req/s",
               "Steady req/min", "p50 ms", "p95 ms", "p99 ms", "Error %", "Peak used MB", "Release"]

ENDPOINTS = {
    "GET /posts": "p95_get_feed_ms",
    "GET /posts/:id": "p95_get_post_ms",
    "GET /users/:id/posts": "p95_get_user_posts_ms",
    "GET /me/posts": "p95_get_my_posts_ms",
    "POST /posts": "p95_create_post_ms",
    "POST /posts/:id/like": "p95_like_ms",
    "DELETE /posts/:id/like": "p95_unlike_ms",
    "POST /posts/:id/comments": "p95_comment_ms",
}

CSV_COLUMNS = [
    # identity
    "run_date", "tag", "git_sha", "vus", "ramp_s", "hold_s",
    # verdict
    "pass", "fail_reasons", "crit_p50_ms", "crit_p95_ms", "crit_p99_ms", "crit_error_pct",
    # stack
    "stack", "language", "runtime", "runtime_version", "framework", "db", "db_version", "db_driver", "db_pool",
    "app_workers", "change",
    # server
    "server_plan", "server_vcpu", "server_ram_mb", "os", "kernel", "swap_mb", "pg_shared_buffers",
    "pg_max_connections", "mem_avail_mb_idle",
    # load generator
    "loadgen", "loadgen_nofile", "k6_version",
    # throughput
    "total_requests", "avg_rps", "steady_requests", "steady_rps", "steady_rpm", "iterations", "vus_max",
    # errors
    "error_rate_pct", "steady_error_rate_pct",
    # latency (steady phase)
    "steady_avg_ms", "steady_p50_ms", "steady_p90_ms", "steady_p95_ms", "steady_p99_ms", "steady_max_ms",
    # latency (whole run)
    "run_avg_ms", "run_p50_ms", "run_p90_ms", "run_p95_ms", "run_p99_ms", "run_max_ms",
    # per endpoint p95 (whole run)
    *ENDPOINTS.values(),
    # server resources
    "app_pss_mb_peak", "pg_pss_mb_peak", "mem_used_mb_peak", "mem_avail_mb_min", "swap_used_mb_peak",
    "cpu_total_pct_avg_steady", "cpu_steal_pct_avg_steady", "app_cpu_pct_avg_steady", "pg_cpu_pct_avg_steady",
    "app_conns_peak", "load1_peak",
]


def load_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def metric(k6, name, stat):
    m = k6["metrics"].get(name)
    return None if m is None else m["values"].get(stat)


def fmt(v, digits=1):
    if v is None:
        return "-"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def rnd(v, digits=2):
    return round(v, digits) if isinstance(v, float) else v


def read_env(path):
    env = {}
    try:
        with open(path) as fh:
            for line in fh:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env[k] = v
    except OSError:
        pass
    return env


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


def judge(s, crit):
    lat = s["steady_latency_ms"]
    reasons = []
    for name, key, limit in (("p50", "med", crit.p50), ("p95", "p(95)", crit.p95), ("p99", "p(99)", crit.p99)):
        if lat[key] is None or lat[key] >= limit:
            reasons.append(f"{name} {fmt(lat[key], 0)}>={limit:g}ms")
    if s["error_rate_pct"] >= crit.error_pct:
        reasons.append(f"errors {s['error_rate_pct']:.2f}%>={crit.error_pct:g}%")
    return not reasons, reasons


def upsert_table(path, start, end, columns, row, key_cols):
    with open(path) as fh:
        text = fh.read()
    if start not in text or end not in text:
        print(f"{path}: markers {start} missing, not updated")
        return
    head, rest = text.split(start, 1)
    body, tail = rest.split(end, 1)
    lines = [l for l in body.strip("\n").split("\n") if l.startswith("|")]
    data = lines[2:]
    key = "| " + " | ".join(row[:key_cols]) + " |"
    data = [l for l in data if not l.startswith(key)]
    data.append("| " + " | ".join(row) + " |")
    header = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    with open(path, "w") as fh:
        fh.write(head + start + "\n" + "\n".join(header + data) + "\n" + end + tail)


def upsert_csv(path, record):
    rows = []
    if os.path.exists(path):
        with open(path, newline="") as fh:
            rows = [r for r in csv.DictReader(fh)
                    if not (r.get("tag") == record["tag"] and str(r.get("vus")) == str(record["vus"]))]
    rows.append({k: ("" if v is None else v) for k, v in record.items()})
    rows.sort(key=lambda r: (r.get("run_date", ""), int(r.get("vus") or 0)))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(rows)


def summarize(run_dir, crit):
    run = load_json(os.path.join(run_dir, "run.json"))
    k6 = load_json(os.path.join(run_dir, "k6_summary.json"))
    bench = load_json(os.path.join(run_dir, "bench.json"), {}) or {}
    env = read_env(os.path.join(run_dir, "server_env.txt"))

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
        "bench": bench,
        "server_env": env,
    }
    # Prefer the k6 setup() timestamp; fall back to the wall clock taken before k6 launched.
    # Server samples use the droplet clock — both machines should run NTP.
    started = run["k6_started_at"]
    ms = (load_json(os.path.join(run_dir, "k6_start.json"), {}) or {}).get("started_at_ms")
    if ms:
        started = ms / 1000
    steady_from = started + run["ramp_s"]
    metrics_csv = os.path.join(run_dir, "server_metrics.csv")
    s["server"] = server_stats(metrics_csv, steady_from, steady_from + hold_s) if os.path.exists(metrics_csv) else {}

    passed, reasons = judge(s, crit)
    s["pass"], s["fail_reasons"] = passed, reasons
    s["criteria"] = vars(crit)
    with open(os.path.join(run_dir, "summary.json"), "w") as fh:
        json.dump(s, fh, indent=2)

    srv, lat, rl = s["server"], s["steady_latency_ms"], s["latency_ms"]
    row = [s["tag"], s["stack"], str(s["vus"]), "PASS" if passed else "FAIL", fmt(s["steady_rps"]),
           fmt(s["steady_rpm"], 0), str(s["total_requests"]), fmt(lat["med"]), fmt(lat["p(90)"]), fmt(lat["p(95)"]),
           fmt(lat["p(99)"]), fmt(lat["max"], 0), fmt(s["error_rate_pct"], 2), fmt(srv.get("app_pss_mb_peak"), 0),
           fmt(srv.get("pg_pss_mb_peak"), 0), fmt(srv.get("mem_used_mb_peak"), 0),
           fmt(srv.get("swap_used_mb_peak"), 0), fmt(srv.get("cpu_total_pct_avg_steady")),
           fmt(srv.get("cpu_steal_pct_avg_steady")), s["loadgen"]]

    md = [f"# {s['tag']} — {s['vus']} VUs — {'PASS' if passed else 'FAIL'}", "",
          "| " + " | ".join(RUN_COLUMNS) + " |", "|" + "---|" * len(RUN_COLUMNS), "| " + " | ".join(row) + " |", "",
          f"Criteria: steady p50 < {crit.p50:g} ms, p95 < {crit.p95:g} ms, p99 < {crit.p99:g} ms, "
          f"errors < {crit.error_pct:g} %." + (f" Failed: {', '.join(reasons)}." if reasons else ""), "",
          "Latency columns are steady-state (hold phase). Error % covers the whole run.", "",
          "## p95 by endpoint (ms, whole run)", ""]
    md += [f"- `{k}`: {fmt(v)}" for k, v in sorted(s["per_endpoint_p95_ms"].items())]
    with open(os.path.join(run_dir, "summary.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")

    runtime = bench.get("runtime", "")
    record = {
        "run_date": s.get("date"), "tag": s["tag"], "git_sha": s.get("git_sha"), "vus": s["vus"],
        "ramp_s": s["ramp_s"], "hold_s": hold_s,
        "pass": int(passed), "fail_reasons": "; ".join(reasons),
        "crit_p50_ms": crit.p50, "crit_p95_ms": crit.p95, "crit_p99_ms": crit.p99, "crit_error_pct": crit.error_pct,
        "stack": s["stack"], "language": bench.get("language"), "runtime": runtime,
        "runtime_version": env.get(runtime) or bench.get("runtime_version"), "framework": bench.get("framework"),
        "db": bench.get("db", "postgres"), "db_version": env.get("postgres"), "db_driver": bench.get("db_driver"),
        "db_pool": bench.get("db_pool"), "app_workers": bench.get("workers"), "change": bench.get("change"),
        "server_plan": env.get("plan", "DO Basic $6 (1 vCPU / 1 GB / 25 GB)"), "server_vcpu": env.get("nproc"),
        "server_ram_mb": env.get("mem_total_mb"), "os": env.get("os"), "kernel": env.get("kernel"),
        "swap_mb": env.get("swap_mb"), "pg_shared_buffers": env.get("shared_buffers"),
        "pg_max_connections": env.get("max_connections"), "mem_avail_mb_idle": env.get("mem_avail_mb_idle"),
        "loadgen": s["loadgen"], "loadgen_nofile": s.get("loadgen_nofile"), "k6_version": s.get("k6_version"),
        "total_requests": s["total_requests"], "avg_rps": rnd(s["avg_rps"]), "steady_requests": steady_count,
        "steady_rps": rnd(s["steady_rps"]), "steady_rpm": rnd(s["steady_rpm"], 0), "iterations": s["iterations"],
        "vus_max": s["vus_max"], "error_rate_pct": rnd(s["error_rate_pct"], 3),
        "steady_error_rate_pct": rnd(s["steady_error_rate_pct"], 3),
        **{f"steady_{n}_ms": rnd(lat[k]) for n, k in
           (("avg", "avg"), ("p50", "med"), ("p90", "p(90)"), ("p95", "p(95)"), ("p99", "p(99)"), ("max", "max"))},
        **{f"run_{n}_ms": rnd(rl[k]) for n, k in
           (("avg", "avg"), ("p50", "med"), ("p90", "p(90)"), ("p95", "p(95)"), ("p99", "p(99)"), ("max", "max"))},
        **{col: rnd(s["per_endpoint_p95_ms"].get(name)) for name, col in ENDPOINTS.items()},
        **{k: rnd(v) for k, v in srv.items()},
    }
    return s, row, record


def capacity(tag_dir, crit, readme):
    runs = [load_json(p) for p in glob.glob(os.path.join(tag_dir, "vus-*", "summary.json"))]
    runs = sorted((r for r in runs if r), key=lambda r: r["vus"])
    passed = [r for r in runs if r["pass"]]
    failed = [r for r in runs if not r["pass"]]
    best = passed[-1] if passed else None
    first_fail = min((r["vus"] for r in failed if not best or r["vus"] > best["vus"]), default=None)
    cap = {
        "tag": os.path.basename(tag_dir.rstrip("/")),
        "criteria": vars(crit),
        "capacity_vus": best["vus"] if best else 0,
        "first_fail_vus": first_fail,
        "levels_tested": [{"vus": r["vus"], "pass": r["pass"], "fail_reasons": r["fail_reasons"]} for r in runs],
        "at_capacity": None if not best else {
            "steady_rps": best["steady_rps"], "steady_rpm": best["steady_rpm"],
            "steady_latency_ms": best["steady_latency_ms"], "error_rate_pct": best["error_rate_pct"],
            "server": best.get("server", {}),
        },
    }
    with open(os.path.join(tag_dir, "capacity.json"), "w") as fh:
        json.dump(cap, fh, indent=2)

    ref = best or (runs[0] if runs else None)
    if ref and readme:
        lat = ref["steady_latency_ms"]
        row = [cap["tag"], ref["stack"], (ref.get("bench") or {}).get("change", "-"),
               str(cap["capacity_vus"]) if best else "< " + str(runs[0]["vus"]),
               str(first_fail) if first_fail else "-",
               fmt(ref["steady_rps"]) if best else "-", fmt(ref["steady_rpm"], 0) if best else "-",
               fmt(lat["med"]) if best else "-", fmt(lat["p(95)"]) if best else "-",
               fmt(lat["p(99)"]) if best else "-", fmt(ref["error_rate_pct"], 2) if best else "-",
               fmt((ref.get("server") or {}).get("mem_used_mb_peak"), 0) if best else "-",
               f"[release]({REPO}/releases/tag/{cap['tag']})"]
        upsert_table(readme, CAP_START, CAP_END, CAP_COLUMNS, row, 1)
    print(json.dumps({k: cap[k] for k in ("tag", "capacity_vus", "first_fail_vus")}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--capacity", metavar="TAG_DIR")
    ap.add_argument("--readme")
    ap.add_argument("--csv")
    ap.add_argument("--p50", type=float, default=500)
    ap.add_argument("--p95", type=float, default=800)
    ap.add_argument("--p99", type=float, default=1000)
    ap.add_argument("--error-pct", type=float, default=1)
    a = ap.parse_args()
    crit = argparse.Namespace(p50=a.p50, p95=a.p95, p99=a.p99, error_pct=a.error_pct)

    if a.capacity:
        capacity(a.capacity, crit, a.readme)
        return
    if not a.run_dir:
        ap.error("run_dir or --capacity required")
    s, row, record = summarize(a.run_dir, crit)
    if a.readme:
        upsert_table(a.readme, RUNS_START, RUNS_END, RUN_COLUMNS, row, 3)
    if a.csv:
        upsert_csv(a.csv, record)
    print("| " + " | ".join(row) + " |")
    print(f"pass={int(s['pass'])}")
    print(f"fail_reasons={'; '.join(s['fail_reasons'])}")
    print(f"error_rate_pct={s['error_rate_pct']:.2f}")


if __name__ == "__main__":
    main()
