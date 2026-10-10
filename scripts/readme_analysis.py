#!/usr/bin/env python3
"""Rebuild README's "Analysis per configuration" section from every results/<tag>/config.md.

Copies each tag's "What changed", "Summary", "Observations" and "Next idea" sections verbatim between
<!-- ANALYSIS:START --> and <!-- ANALYSIS:END -->, so the README carries the full analysis without hand copying.
Tags whose config.md still has template placeholders are skipped. Run by release.sh; safe to run any time.

Usage: python3 -I scripts/readme_analysis.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
RESULTS = ROOT / "results"
START, END = "<!-- ANALYSIS:START -->", "<!-- ANALYSIS:END -->"
SECTIONS = [  # (heading in config.md, heading in README)
    ("What changed vs. the previous tag", "What changed"),
    ("Summary", "Summary"),
    ("Observations", "Observations"),
    ("Next idea", "Next idea"),
]
PLACEHOLDERS = ("<!-- Analysis written after the test", "<!-- ONE variable per tag")
REPO_URL = "https://github.com/programmerpranit/1gb-server-test"


def sections(text):
    out, name, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if name:
                out[name] = "\n".join(buf).strip()
            name, buf = line[3:].strip(), []
        elif name:
            buf.append(line)
    if name:
        out[name] = "\n".join(buf).strip()
    return out


def tag_key(tag):
    # Group by stack, then by version number: node-express-v02-pool -> ("node-express", 2)
    m = re.match(r"(.+)-v(\d+)-", tag)
    return (m.group(1), int(m.group(2))) if m else (tag, 0)


def build():
    blocks = []
    for cfg in sorted(RESULTS.glob("*/config.md"), key=lambda p: tag_key(p.parent.name)):
        text = cfg.read_text()
        if any(p in text for p in PLACEHOLDERS):
            continue
        tag = cfg.parent.name
        parts = sections(text)
        lines = [f"### {tag}", "",
                 f"[Full report](results/{tag}/config.md) · [Release]({REPO_URL}/releases/tag/{tag})"]
        for src, title in SECTIONS:
            body = parts.get(src)
            if body:
                lines += ["", f"#### {title}", "", body]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "_No released configurations yet._"


def main():
    readme = README.read_text()
    if START not in readme or END not in readme:
        raise SystemExit(f"README.md has no {START} ... {END} markers")
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{build()}\n{END}{tail}")


if __name__ == "__main__":
    main()
