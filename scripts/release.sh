#!/usr/bin/env bash
# Commit results for a tag, create an annotated git tag and a GitHub release with
# the app source ("build") and result files attached.
#
# Usage: scripts/release.sh <tag>
# Requires: clean working tree except results/<tag>/ and README.md, a GitHub remote, `gh auth login`.
source "$(dirname "$0")/lib.sh"
TAG="${1:?usage: release.sh <tag>}"
TAG_DIR="results/$TAG"
cd "$REPO_ROOT"

[[ -d "$TAG_DIR" ]] || { echo "$TAG_DIR not found — run scripts/run_test.sh $TAG first"; exit 1; }
git rev-parse "$TAG" >/dev/null 2>&1 && { echo "tag $TAG already exists"; exit 1; }
git remote get-url origin >/dev/null 2>&1 || { echo "no 'origin' remote — create one: gh repo create"; exit 1; }
if ! git diff --quiet HEAD -- apps db loadtest scripts || [[ -n "$(git ls-files --others --exclude-standard apps db loadtest scripts)" ]]; then
  echo "Uncommitted changes in apps/ db/ loadtest/ scripts/ — commit the code you tested first"; exit 1
fi
if grep -qE '<!-- (ONE variable per tag|Analysis written after the test)' "$TAG_DIR/config.md"; then
  echo "Fill in $TAG_DIR/config.md (Summary, What changed, ...) before releasing"; exit 1
fi

STACK="$(python3 -I -c "import json,glob,sys; print(json.load(open(sorted(glob.glob(sys.argv[1]+'/vus-*/run.json'))[0]))['stack'])" "$TAG_DIR")"

git add "$TAG_DIR" README.md results/results.csv
git commit -m "results: $TAG" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true
git tag -a "$TAG" -m "Benchmark $TAG ($STACK)"
git push origin HEAD
git push origin "$TAG"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
if [[ -d "apps/$STACK" ]]; then
  git archive --format=tar.gz -o "$WORK/build-$TAG.tgz" "$TAG" "apps/$STACK" db loadtest scripts
fi
tar -czf "$WORK/results-$TAG.tgz" "$TAG_DIR"

{
  cat "$TAG_DIR/config.md"
  echo; echo "## Capacity"; echo
  [[ -f "$TAG_DIR/capacity.json" ]] && echo '```json' && cat "$TAG_DIR/capacity.json" && echo '```'
  echo; echo "## Results"; echo
  for f in $(ls "$TAG_DIR"/vus-*/summary.md | sort -t- -k2 -n); do sed '1d' "$f"; echo; done
} > "$WORK/notes.md"

gh release create "$TAG" --title "$TAG" --notes-file "$WORK/notes.md" "$WORK"/*.tgz
log "Released $TAG"
