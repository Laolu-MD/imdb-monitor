import os
import json
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Configuration
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")
WATCHLIST_FILE = "watchlist.csv"
METADATA_CACHE_FILE = "metadata_cache.json"
HISTORY_FILE = "rating_history.csv"
REPORT_FILE = "latest_report.txt"
RATINGS_API = "https://api.agregarr.org/api/ratings"
OMDB_API = "https://www.omdbapi.com/"
CACHE_MAX_AGE_DAYS = 180

def load_csv(path, fieldnames=None):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def save_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def load_json(path):
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_omdb(imdb_id):
    if not OMDB_API_KEY:
        return None
    try:
        r = requests.get(OMDB_API, params={"i": imdb_id, "apikey": OMDB_API_KEY}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("Response") == "True":
            return data
    except Exception as e:
        print(f"OMDb error for {imdb_id}: {e}")
    return None

def fetch_ratings_batch(imdb_ids):
    if not imdb_ids:
        return {}
    params = [("id", iid) for iid in imdb_ids]
    try:
        r = requests.get(RATINGS_API, params=params, timeout=20)
        r.raise_for_status()
        results = r.json()
        return {item["imdbId"]: item for item in results if item.get("rating") is not None}
    except Exception as e:
        print(f"Ratings API error: {e}")
        return {}

def main():
    now = datetime.now(timezone.utc)
    print(f"Starting monitor at {now.isoformat()}")

    watchlist = load_csv(WATCHLIST_FILE)
    if not watchlist:
        print("No watchlist found. Create watchlist.csv first.")
        return

    metadata_cache = load_json(METADATA_CACHE_FILE)
    history = load_csv(HISTORY_FILE)

    # Build last known rating map
    last_rating = {}
    for row in history:
        last_rating[row["imdb_id"]] = {
            "rating": float(row["rating"]) if row.get("rating") else None,
            "votes": int(row["votes"]) if row.get("votes") else None,
            "date": row.get("date", "")
        }

    changes = []
    ids_to_rate = []
    cache_updated = False

    for movie in watchlist:
        imdb_id = movie.get("imdb_id", "").strip()
        if not imdb_id:
            continue

        # Enrich metadata if missing or old
        meta = metadata_cache.get(imdb_id, {})
        cached_at = meta.get("cached_at")
        needs_refresh = True
        if cached_at:
            try:
                cached_dt = datetime.fromisoformat(cached_at)
                age = (now - cached_dt).days
                if age < CACHE_MAX_AGE_DAYS and meta.get("title"):
                    needs_refresh = False
            except Exception:
                pass

        if needs_refresh:
            print(f"Fetching metadata for {imdb_id}...")
            omdb_data = fetch_omdb(imdb_id)
            if omdb_data:
                metadata_cache[imdb_id] = {
                    "title": omdb_data.get("Title"),
                    "year": omdb_data.get("Year"),
                    "rated": omdb_data.get("Rated"),
                    "genre": omdb_data.get("Genre"),
                    "director": omdb_data.get("Director"),
                    "actors": omdb_data.get("Actors"),
                    "language": omdb_data.get("Language"),
                    "country": omdb_data.get("Country"),
                    "boxoffice": omdb_data.get("BoxOffice"),
                    "runtime": omdb_data.get("Runtime"),
                    "plot": omdb_data.get("Plot"),
                    "cached_at": now.isoformat()
                }
                cache_updated = True
                time.sleep(0.3)  # be polite
            else:
                print(f"  Failed to fetch metadata for {imdb_id}")

        ids_to_rate.append(imdb_id)

    # Fetch current ratings in batches of 50
    ratings_map = {}
    for i in range(0, len(ids_to_rate), 50):
        batch = ids_to_rate[i:i+50]
        ratings_map.update(fetch_ratings_batch(batch))
        time.sleep(0.5)

    # Process changes and history
    new_history_rows = []
    for movie in watchlist:
        imdb_id = movie.get("imdb_id", "").strip()
        if not imdb_id:
            continue

        current = ratings_map.get(imdb_id, {})
        curr_rating = current.get("rating")
        curr_votes = current.get("votes")

        prev = last_rating.get(imdb_id, {})
        prev_rating = prev.get("rating")

        change_str = ""
        if curr_rating is not None and prev_rating is not None:
            delta = round(curr_rating - prev_rating, 1)
            if delta != 0:
                change_str = f"{'+' if delta > 0 else ''}{delta}"
                changes.append({
                    "imdb_id": imdb_id,
                    "title": movie.get("title") or metadata_cache.get(imdb_id, {}).get("title", ""),
                    "old": prev_rating,
                    "new": curr_rating,
                    "delta": delta,
                    "votes": curr_votes,
                    "priority": movie.get("priority", ""),
                    "watched": movie.get("watched", ""),
                    "in_library": movie.get("in_library", "")
                })

        new_history_rows.append({
            "date": now.strftime("%Y-%m-%d"),
            "imdb_id": imdb_id,
            "title": movie.get("title") or metadata_cache.get(imdb_id, {}).get("title", ""),
            "rating": curr_rating if curr_rating is not None else "",
            "votes": curr_votes if curr_votes is not None else "",
            "change": change_str
        })

    # Append history (keep last 365 days roughly by not pruning here)
    history.extend(new_history_rows)
    # Optional: keep only last N rows to avoid huge files
    if len(history) > 10000:
        history = history[-10000:]

    history_fields = ["date", "imdb_id", "title", "rating", "votes", "change"]
    save_csv(HISTORY_FILE, history, history_fields)

    if cache_updated:
        save_json(METADATA_CACHE_FILE, metadata_cache)

    # Generate report
    report_lines = [
        f"IMDb Rating Monitor Report",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Watchlist size: {len(watchlist)}",
        f"Changes detected: {len(changes)}",
        ""
    ]

    if changes:
        report_lines.append("=== Rating Changes ===")
        for c in sorted(changes, key=lambda x: abs(x["delta"]), reverse=True):
            report_lines.append(
                f"{c['title']} ({c['imdb_id']})  {c['old']} → {c['new']} ({c['delta']:+.1f})  votes={c['votes']}  "
                f"priority={c['priority']} watched={c['watched']} in_library={c['in_library']}"
            )
    else:
        report_lines.append("No rating changes detected.")

    report_lines.append("")
    report_lines.append("=== Current Status (top priority) ===")
    prioritized = sorted(watchlist, key=lambda m: int(m.get("priority") or 0), reverse=True)
    for m in prioritized[:20]:
        iid = m.get("imdb_id", "")
        meta = metadata_cache.get(iid, {})
        rating_info = ratings_map.get(iid, {})
        report_lines.append(
            f"{m.get('title') or meta.get('title','')} ({iid})  "
            f"rating={rating_info.get('rating','?')}  "
            f"priority={m.get('priority','')}  watched={m.get('watched','')}  in_library={m.get('in_library','')}  "
            f"country={meta.get('country','')}  genre={meta.get('genre','')}"
        )

    report_text = "\n".join(report_lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print("Done.")

if __name__ == "__main__":
    main()
