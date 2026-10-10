#!/usr/bin/env bash
# Commit results for a tag, create an annotated git tag and a GitHub release with
# the app source ("build") and result files attached.
#
# Usage: scripts/release.sh <tag>            first release of a tag
#        scripts/release.sh --update <tag>   after adding VU levels to an already released tag: commit + push the
#                                            new results, re-upload results-<tag>.tgz and refresh the release notes
#                                            (the git tag itself is not moved)
# Requires: committed code in apps/ db/ loadtest/ scripts/, a GitHub remote, `gh auth login`.
source "$(dirname "$0")/lib.sh"
UPDATE=0
[[ "${1:-}" == "--update" ]] && { UPDATE=1; shift; }
TAG="${1:?usage: release.sh [--update] <tag>}"
TAG_DIR="results/$TAG"
cd "$REPO_ROOT"

[[ -d "$TAG_DIR" ]] || { echo "$TAG_DIR not found — run scripts/run_test.sh $TAG first"; exit 1; }
if [[ $UPDATE == 1 ]]; then
  git rev-parse "$TAG" >/dev/null 2>&1 || { echo "tag $TAG does not exist — release it without --update"; exit 1; }
else
  git rev-parse "$TAG" >/dev/null 2>&1 && { echo "tag $TAG already exists — use --update to refresh its release"; exit 1; }
fi
git remote get-url origin >/dev/null 2>&1 || { echo "no 'origin' remote — create one: gh repo create"; exit 1; }
if ! git diff --quiet HEAD -- apps db loadtest scripts || [[ -n "$(git ls-files --others --exclude-standard apps db loadtest scripts)" ]]; then
  echo "Uncommitted changes in apps/ db/ loadtest/ scripts/ — commit the code you tested first"; exit 1
fi
if grep -qE '<!-- (ONE variable per tag|Analysis written after the test)' "$TAG_DIR/config.md"; then
  echo "Fill in $TAG_DIR/config.md (Summary, What changed, ...) before releasing"; exit 1
fi

STACK="$(python3 -I -c "import json,glob,sys; print(json.load(open(sorted(glob.glob(sys.argv[1]+'/vus-*/run.json'))[0]))['stack'])" "$TAG_DIR")"
LEVELS="$(python3 -I -c "import glob,re,sys; print(' '.join(sorted((re.search(r'vus-(\d+)', p).group(1) for p in glob.glob(sys.argv[1]+'/vus-*')), key=int)))" "$TAG_DIR")"

# Visual report with charts (k6 time series + server samples): results/<tag>/report.html
python3 -I scripts/report_html.py "$TAG_DIR" >/dev/null

git add "$TAG_DIR" README.md results/results.csv
[[ -f CLAUDE.md ]] && git add CLAUDE.md
MSG="results: $TAG"; [[ $UPDATE == 1 ]] && MSG="results: $TAG (levels $LEVELS)"
git commit -m "$MSG" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NhgEjqV5ffFqEtCZcfWRbP" || true
[[ $UPDATE == 0 ]] && git tag -a "$TAG" -m "Benchmark $TAG ($STACK)"
git push origin HEAD
[[ $UPDATE == 0 ]] && git push origin "$TAG"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
tar -czf "$WORK/results-$TAG.tgz" "$TAG_DIR"
cp "$TAG_DIR/report.html" "$WORK/report-$TAG.html"

{
  echo "> **Charts:** download \`report-$TAG.html\` below and open it in a browser."
  echo
  cat "$TAG_DIR/config.md"
  echo; echo "## Capacity"; echo
  [[ -f "$TAG_DIR/capacity.json" ]] && echo '```json' && cat "$TAG_DIR/capacity.json" && echo '```'
  echo; echo "## Results"; echo
  for v in $LEVELS; do sed '1d' "$TAG_DIR/vus-$v/summary.md"; echo; done
  if [[ $UPDATE == 1 ]]; then
    echo "_Updated $(date -u +%Y-%m-%d) with levels $LEVELS at commit $(git rev-parse --short HEAD). The git tag still"
    echo "points at the commit of the first release; app code is unchanged (see git_sha in each run.json)._"
  fi
} > "$WORK/notes.md"

if [[ $UPDATE == 1 ]]; then
  gh release upload "$TAG" "$WORK/results-$TAG.tgz" "$WORK/report-$TAG.html" --clobber
  gh release edit "$TAG" --notes-file "$WORK/notes.md" >/dev/null
  log "Updated release $TAG"
else
  [[ -d "apps/$STACK" ]] && git archive --format=tar.gz -o "$WORK/build-$TAG.tgz" "$TAG" "apps/$STACK" db loadtest scripts
  gh release create "$TAG" --title "$TAG" --notes-file "$WORK/notes.md" "$WORK"/*.tgz "$WORK/report-$TAG.html"
  log "Released $TAG"
fi
