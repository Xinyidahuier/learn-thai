#!/usr/bin/env python3
"""
One-time migration: videos.json -> articles.json with new fields.
Adds: type, status, created_at, favorite.
Renames video_id -> article_id in sentences.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def migrate():
    videos_file = DATA / "videos.json"
    articles_file = DATA / "articles.json"
    sentences_file = DATA / "sentences.json"

    videos = json.loads(videos_file.read_text()) if videos_file.exists() else []
    sentences = json.loads(sentences_file.read_text()) if sentences_file.exists() else []

    now = datetime.now(timezone.utc).isoformat()
    articles = []
    for v in videos:
        articles.append({
            "id": v["id"],
            "title": v.get("title", v["id"]),
            "type": "youtube" if v.get("url", "").startswith("http") else "audio",
            "source_url": v.get("url", ""),
            "duration_sec": v.get("duration_sec", 0),
            "duration_str": v.get("duration_str", ""),
            "sentence_count": v.get("sentence_count", 0),
            "status": "studying",
            "favorite": False,
            "created_at": now,
        })

    # Rename video_id -> article_id in sentences (keep video_id for safety)
    for s in sentences:
        if "video_id" in s and "article_id" not in s:
            s["article_id"] = s["video_id"]

    articles_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    sentences_file.write_text(json.dumps(sentences, ensure_ascii=False, indent=2))

    # Keep old videos.json for safety but flag
    print(f"  ↳ {len(articles)} articles migrated")
    print(f"  ↳ {len(sentences)} sentences updated with article_id")
    print(f"  ℹ️  videos.json preserved as legacy — safe to delete after verifying")


if __name__ == "__main__":
    migrate()
    print("✅ Migration done")
