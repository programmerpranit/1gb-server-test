#!/usr/bin/env python3
"""Convert Twitterdatainsheets.xlsx into clean CSVs ready for Postgres COPY.

Stdlib only (no openpyxl). Reads the xlsx as a zip of XML files.

Usage: python3 -I scripts/xlsx_to_csv.py [xlsx_path] [out_dir]
Defaults: Twitterdatainsheets.xlsx -> data/

Outputs:
  data/users.csv      id,handle,gender
  data/locations.csv  id,country,state,state_code,city
  data/posts.csv      id,external_id,user_id,location_id,text,lang,is_reshare,
                      reach,retweet_count,like_count,klout,sentiment,created_at
  data/meta.json      row counts the load test needs (USER_COUNT, AUTHOR_COUNT, POST_COUNT)

Transformations (see CLAUDE.md "Dataset"):
  - Cells are mapped by column letter, headers are stripped of whitespace.
  - The trailing all-"NULL" row of every sheet is dropped; "NULL" cells become empty (SQL NULL).
  - Users are de-duplicated (first occurrence wins); rows with malformed IDs are dropped.
  - Tweet authors missing from the User sheet get a stub user (gender NULL).
  - Users get sequential bigint IDs: authors first (1..AUTHOR_COUNT), then everyone else.
  - Posts are sorted by tweet ID (= time order) and get sequential bigint IDs 1..POST_COUNT.
  - created_at is decoded from the Twitter snowflake ID.
"""
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TWEET_ID = re.compile(r"tw-(\d+)")
TWITTER_EPOCH_MS = 1288834974657


def shared_strings(zf):
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(NS + "t")) for si in root]


def sheet_paths(zf):
    """Map sheet name -> xml path inside the zip."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {r.get("Id"): r.get("Target") for r in rels}
    rid_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    out = {}
    for s in wb.iter(NS + "sheet"):
        target = rid_to_target[s.get(rid_attr)].lstrip("/")
        out[s.get("name")] = target if target.startswith("xl/") else "xl/" + target
    return out


def iter_rows(zf, path, strings):
    """Yield dicts keyed by stripped header name. 'NULL' -> None."""
    header = None
    with zf.open(path) as fh:
        for _, el in ET.iterparse(fh):
            if el.tag != NS + "row":
                continue
            cells = {}
            for c in el:
                col = re.match(r"[A-Z]+", c.get("r")).group()
                v = c.find(NS + "v")
                val = v.text if v is not None else None
                if val is not None and c.get("t") == "s":
                    val = strings[int(val)]
                cells[col] = val
            el.clear()
            if header is None:
                header = {col: (name or "").strip() for col, name in cells.items()}
                continue
            row = {}
            for col, name in header.items():
                val = cells.get(col)
                row[name] = None if val in (None, "NULL") else val
            yield row


def parse_tweet_id(value):
    m = TWEET_ID.fullmatch(value or "")
    return int(m.group(1)) if m else None


def snowflake_time(tweet_id):
    ms = (tweet_id >> 22) + TWITTER_EPOCH_MS
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def to_int(value):
    return None if value is None else int(float(value))


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else "Twitterdatainsheets.xlsx"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    os.makedirs(out_dir, exist_ok=True)
    stats = {}

    with zipfile.ZipFile(xlsx) as zf:
        strings = shared_strings(zf)
        paths = sheet_paths(zf)

        # Locations
        locations = []
        for r in iter_rows(zf, paths["Location"], strings):
            if r["LocationID"] is None or not r["LocationID"].isdigit():
                continue
            locations.append([int(r["LocationID"]), r["Country"], r["State"], r["StateCode"], r["City"]])
        location_ids = {l[0] for l in locations}

        # Users (dedupe, drop malformed)
        genders = {}
        dropped_users = 0
        for r in iter_rows(zf, paths["User"], strings):
            handle = r["UserID"]
            if parse_tweet_id(handle) is None:
                dropped_users += 1
                continue
            genders.setdefault(handle, r["Gender"])
        stats["user_rows_dropped_malformed"] = dropped_users

        # Tweets
        tweets = []
        for r in iter_rows(zf, paths["Tweet"], strings):
            tid = parse_tweet_id(r["TweetID"])
            if tid is None or parse_tweet_id(r["UserID"]) is None:
                continue
            loc = to_int(r["LocationID"])
            tweets.append({
                "external_id": tid,
                "handle": r["UserID"],
                "location_id": loc if loc in location_ids else None,
                "text": r["text"] or "",
                "lang": r["Lang"],
                "is_reshare": "true" if r["IsReshare"] in ("1", "true", "TRUE") else "false",
                "reach": to_int(r["Reach"]),
                "retweet_count": to_int(r["RetweetCount"]),
                "like_count": to_int(r["Likes"]) or 0,
                "klout": to_int(r["Klout"]),
                "sentiment": r["Sentiment"],
            })

    tweets.sort(key=lambda t: t["external_id"])

    # Assign user IDs: authors first (in order of first post), then the rest.
    user_ids = {}
    stub_users = 0
    for t in tweets:
        if t["handle"] not in user_ids:
            user_ids[t["handle"]] = len(user_ids) + 1
            if t["handle"] not in genders:
                genders[t["handle"]] = None
                stub_users += 1
    author_count = len(user_ids)
    for handle in genders:
        if handle not in user_ids:
            user_ids[handle] = len(user_ids) + 1

    with open(os.path.join(out_dir, "locations.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "country", "state", "state_code", "city"])
        w.writerows(locations)

    with open(os.path.join(out_dir, "users.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "handle", "gender"])
        for handle, uid in sorted(user_ids.items(), key=lambda kv: kv[1]):
            w.writerow([uid, handle, genders[handle]])

    with open(os.path.join(out_dir, "posts.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "external_id", "user_id", "location_id", "text", "lang", "is_reshare",
                    "reach", "retweet_count", "like_count", "klout", "sentiment", "created_at"])
        for i, t in enumerate(tweets, start=1):
            w.writerow([i, t["external_id"], user_ids[t["handle"]], t["location_id"], t["text"],
                        t["lang"], t["is_reshare"], t["reach"], t["retweet_count"], t["like_count"],
                        t["klout"], t["sentiment"], snowflake_time(t["external_id"])])

    meta = {
        "USER_COUNT": len(user_ids),
        "AUTHOR_COUNT": author_count,
        "POST_COUNT": len(tweets),
        "LOCATION_COUNT": len(locations),
        "stub_users_added": stub_users,
        **stats,
    }
    with open(os.path.join(out_dir, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
