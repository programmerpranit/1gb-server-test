#!/usr/bin/env bash
# Runs ON THE SERVER (via scripts/parity.sh): the parity request list against the app on 127.0.0.1:3000.
U=http://127.0.0.1:3000
r() { local out; out=$(curl -s -w ' |%{http_code}|%{content_type}' "$@"); echo "$* => ${out}" | sed -E 's/"created_at":"[^"]*"/"created_at":"T"/g'; }
J='-H Content-Type:application/json'
r $U/health
r "$U/posts?limit=3"; r "$U/posts?limit=2&before=50"; r "$U/posts?limit=0"; r "$U/posts?limit=51"; r "$U/posts?limit=abc"; r "$U/posts?before=-1"; r "$U/posts/"
r $U/posts/5; r $U/posts/0; r $U/posts/999999; r $U/posts/abc
r "$U/users/7/posts?limit=2"; r "$U/users/99999/posts"; r "$U/users/x/posts"
r $U/me/posts; r -H 'X-User-Id: abc' $U/me/posts; r -H 'X-User-Id: 7' "$U/me/posts?limit=2"
r -X POST $U/posts; r -X POST -H 'X-User-Id: 7' $J -d '{"text":""}' $U/posts; r -X POST -H 'X-User-Id: 7' $J -d '{"text":"hi","is_public":"no"}' $U/posts
r -X POST -H 'X-User-Id: 7' $J -d '{bad' $U/posts; r -X POST -H 'X-User-Id: 7' $J -d '{"text":"parity post","is_public":false}' $U/posts
r -X POST -H 'X-User-Id: 999999' $J -d '{"text":"x"}' $U/posts
r -X POST -H 'X-User-Id: 7' $U/posts/5/like; r -X POST -H 'X-User-Id: 7' $U/posts/5/like; r -X POST -H 'X-User-Id: 7' $U/posts/999999/like; r -X POST $U/posts/5/like
r -X DELETE -H 'X-User-Id: 7' $U/posts/5/like; r -X DELETE -H 'X-User-Id: 7' $U/posts/5/like; r -X DELETE -H 'X-User-Id: 7' $U/posts/999999/like
r -X POST -H 'X-User-Id: 7' $J -d '{"text":"c1"}' $U/posts/5/comments; r -X POST -H 'X-User-Id: 7' $J -d '{"text":"c1"}' $U/posts/999999/comments; r -X POST -H 'X-User-Id: 999999' $J -d '{"text":"c1"}' $U/posts/5/comments; r -X POST -H 'X-User-Id: 7' $J -d '{}' $U/posts/5/comments
r $U/posts/5; r $U/nope; r -X PUT $U/posts
r -D - -o /dev/null "$U/posts?limit=1" | grep -i server-timing | sed 's/[0-9.]\+/N/g'
