#!/usr/bin/env python3
"""
IMDb High Score Monitor
Daily download official datasets, filter high-rated movies, track changes.
Lightweight CSV output, suitable for GitHub Actions.
"""

import os
import gzip
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from io import TextIOWrapper
from urllib.request import urlretrieve

# ==================== Configuration ====================
MIN_RATING = float(os.environ.get("MIN_RATING", "8.0"))
MIN_VOTES = int(os.environ.get("MIN_VOTES", "10000"))
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")
MAX_OMDB_PER_RUN = int(os.environ.get("MAX_OMDB_PER_RUN", "20"))  # limit OMDb calls

DATA_DIR = Path("data")
HISTORY_DIR = Path("history")
CACHE_FILE = Path("metadata_cache.json")
REPORT_FILE = Path("latest_report.txt")
CHANGES_FILE = Path("rating_changes.csv")

BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"

# =======================================================

def download(url: str, dest: Path):
    print(f"Downloading {url}...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, dest)
    print(f"  Saved to {dest}")

def load_gzip_tsv(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)

def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_omdb(imdb_id: str):
    if not OMDB_API_KEY:
        return None
    try:
        import requests
        r = requests.get(
            "https://www.omdbapi.com/",
            params={"i": imdb_id, "apikey": OMDB_API_KEY},
            timeout=15
        )
        data = r.json()
        if data.get("Response") == "True":
            return {
                "rated": data.get("Rated"),
                "genre": data.get("Genre"),
                "director": data.get("Director"),
                "actors": data.get("Actors"),
                "language": data.get("Language"),
                "country": data.get("Country"),
                "boxoffice": data.get("BoxOffice"),
                "runtime": data.get("Runtime"),
            }
    except Exception as e:
        print(f"OMDb error {imdb_id}: {e}")
    return None

def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    print(f"=== IMDb High Score Monitor {today} ===")
    print(f"Filter: rating >= {MIN_RATING}, votes >= {MIN_VOTES}")

    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)

    basics_path = DATA_DIR / "title.basics.tsv.gz"
    ratings_path = DATA_DIR / "title.ratings.tsv.gz"

    # Download fresh data
    download(BASICS_URL, basics_path)
    download(RATINGS_URL, ratings_path)

    print("Parsing datasets...")
    basics = {row["tconst"]: row for row in load_gzip_tsv(basics_path) if row.get("titleType") == "movie"}
    ratings = load_gzip_tsv(ratings_path)

    # Build high-score list
    high_score = []
    for r in ratings:
        try:
            rating = float(r["averageRating"])
            votes = int(r["numVotes"])
        except (ValueError, KeyError):
            continue
        if rating >= MIN_RATING and votes >= MIN_VOTES:
            tconst = r["tconst"]
            basic = basics.get(tconst, {})
            high_score.append({
                "imdb_id": tconst,
                "title": basic.get("primaryTitle", ""),
                "year": basic.get("startYear", ""),
                "rating": rating,
                "votes": votes,
                "genres": basic.get("genres", "").replace(",", " | "),
                "runtime": basic.get("runtimeMinutes", ""),
            })

    high_score.sort(key=lambda x: (-x["rating"], -x["votes"]))
    print(f"Found {len(high_score)} high-score movies")

    # Save today's full snapshot
    today_file = HISTORY_DIR / f"{today}.csv"
    fieldnames = ["imdb_id", "title", "year", "rating", "votes", "genres", "runtime"]
    with open(today_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(high_score)
    # Also write a convenient latest.csv
    latest_file = Path("latest.csv")
    with open(latest_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(high_score)
    print(f"Saved latest.csv")

    # Load previous day for comparison
    prev_files = sorted(HISTORY_DIR.glob("*.csv"))
    prev_map = {}
    if len(prev_files) >= 2:
        prev_file = prev_files[-2]
        with open(prev_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                prev_map[row["imdb_id"]] = {
                    "rating": float(row["rating"]),
                    "title": row["title"]
                }
        print(f"Compared with previous: {prev_file.name}")

    # Detect changes
    changes = []
    current_ids = {m["imdb_id"] for m in high_score}
    prev_ids = set(prev_map.keys())

    for m in high_score:
        iid = m["imdb_id"]
        if iid not in prev_map:
            changes.append({**m, "change_type": "NEW", "delta": ""})
        else:
            old = prev_map[iid]["rating"]
            delta = round(m["rating"] - old, 1)
            if delta != 0:
                changes.append({**m, "change_type": "CHANGED", "delta": f"{delta:+.1f}", "old_rating": old})

    dropped = prev_ids - current_ids
    for iid in dropped:
        changes.append({
            "imdb_id": iid,
            "title": prev_map[iid]["title"],
            "change_type": "DROPPED",
            "rating": "",
            "delta": "",
            "old_rating": prev_map[iid]["rating"]
        })

    # Optional OMDb enrichment for new or top changed
    metadata_cache = load_json(CACHE_FILE)
    omdb_calls = 0
    for ch in changes:
        if omdb_calls >= MAX_OMDB_PER_RUN:
            break
        iid = ch["imdb_id"]
        if iid not in metadata_cache and OMDB_API_KEY:
            print(f"Enriching {iid} via OMDb...")
            meta = fetch_omdb(iid)
            if meta:
                metadata_cache[iid] = {**meta, "cached_at": now.isoformat()}
                omdb_calls += 1
                time.sleep(0.4)

    if omdb_calls:
        save_json(CACHE_FILE, metadata_cache)

    # Append changes to long-term history
    change_fields = ["date", "imdb_id", "title", "change_type", "rating", "votes", "delta", "old_rating"]
    change_rows = []
    for ch in changes:
        change_rows.append({
            "date": today,
            "imdb_id": ch.get("imdb_id", ""),
            "title": ch.get("title", ""),
            "change_type": ch.get("change_type", ""),
            "rating": ch.get("rating", ""),
            "votes": ch.get("votes", ""),
            "delta": ch.get("delta", ""),
            "old_rating": ch.get("old_rating", ""),
        })

    file_exists = CHANGES_FILE.exists()
    with open(CHANGES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=change_fields)
        if not file_exists:
            writer.writeheader()
        writer.writerows(change_rows)

    # Generate human-readable report
    lines = [
        f"IMDb High Score Monitor Report",
        f"Date: {today}",
        f"Filter: rating >= {MIN_RATING}, votes >= {MIN_VOTES}",
        f"Total high-score movies: {len(high_score)}",
        f"New: {sum(1 for c in changes if c['change_type']=='NEW')}",
        f"Changed: {sum(1 for c in changes if c['change_type']=='CHANGED')}",
        f"Dropped: {sum(1 for c in changes if c['change_type']=='DROPPED')}",
        "",
        "=== Top 20 Current High Score ===",
    ]
    for m in high_score[:20]:
        lines.append(f"{m['rating']:.1f}  {m['title']} ({m['year']})  [{m['imdb_id']}]  votes={m['votes']:,}")

    if changes:
        lines.append("")
        lines.append("=== Changes ===")
        for ch in sorted(changes, key=lambda x: abs(float(x.get("delta") or 0) if x.get("delta") else 0), reverse=True)[:30]:
            if ch["change_type"] == "NEW":
                lines.append(f"NEW     {ch.get('rating','')}  {ch['title']} ({ch.get('year','')})  [{ch['imdb_id']}]")
            elif ch["change_type"] == "CHANGED":
                lines.append(f"CHANGE  {ch.get('old_rating','')} → {ch.get('rating','')} ({ch.get('delta','')})  {ch['title']}  [{ch['imdb_id']}]")
            else:
                lines.append(f"DROPPED {ch.get('old_rating','')}  {ch['title']}  [{ch['imdb_id']}]")

    report = "\n".join(lines)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nDone. Snapshot: {today_file}")

if __name__ == "__main__":
    main()
