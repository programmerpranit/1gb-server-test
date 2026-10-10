#!/usr/bin/env python3
"""Summarise a V8 .cpuprofile (node --cpu-prof): self time by category and by function, idle excluded.

Usage: python3 -I scripts/cpuprofile_summary.py <file.cpuprofile> [--top N]
"""
import argparse
import json
import re
from collections import defaultdict

# First match wins. Matched against the function's script URL (or its name for VM entries without a URL).
CATEGORIES = [
    ("garbage collection", lambda name, url: name == "(garbage collector)"),
    ("V8/native (program)", lambda name, url: name == "(program)"),
    ("pg driver", lambda name, url: re.search(r"node_modules/(pg|pg-protocol|pg-types|pg-pool|pgpass|postgres-[a-z]+)/", url)),
    ("etag (response hashing)", lambda name, url: "node_modules/etag/" in url),
    ("express + middleware", lambda name, url: "node_modules/" in url),
    ("node core (http, net, streams)", lambda name, url: url.startswith("node:")),
    ("app code", lambda name, url: "/src/" in url),
    ("other", lambda name, url: True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    prof = json.load(open(a.profile))
    nodes = {n["id"]: n for n in prof["nodes"]}
    # Self time per node from samples x time deltas (µs).
    self_us = defaultdict(float)
    for node_id, dt in zip(prof["samples"], prof["timeDeltas"]):
        self_us[node_id] += max(dt, 0)
    total = sum(us for nid, us in self_us.items() if nodes[nid]["callFrame"]["functionName"] != "(idle)")
    idle = sum(us for nid, us in self_us.items() if nodes[nid]["callFrame"]["functionName"] == "(idle)")
    wall = (prof["endTime"] - prof["startTime"]) or 1

    by_cat, by_fn = defaultdict(float), defaultdict(float)
    for nid, us in self_us.items():
        cf = nodes[nid]["callFrame"]
        name, url = cf["functionName"] or "(anonymous)", cf.get("url", "")
        if name == "(idle)":
            continue
        cat = next(c for c, test in CATEGORIES if test(name, url))
        by_cat[cat] += us
        where = re.sub(r"^.*node_modules/", "", url) or url
        by_fn[(name, f"{where}:{cf.get('lineNumber', -1) + 1}" if url else "")] += us

    print(f"V8 CPU profile: {wall / 1e6:.1f} s wall, {total / 1e6:.1f} s on-CPU in the main thread "
          f"({100 * total / wall:.0f} %), idle {idle / 1e6:.1f} s. Percentages below are of on-CPU time.\n")
    print("Self time by category")
    for cat, us in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {100 * us / total:5.1f} %  {cat}")
    print(f"\nTop {a.top} functions by self time")
    for (name, where), us in sorted(by_fn.items(), key=lambda kv: -kv[1])[: a.top]:
        print(f"  {100 * us / total:5.1f} %  {name}  {where}")


if __name__ == "__main__":
    main()
