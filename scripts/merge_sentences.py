#!/usr/bin/env python3
"""
Merge fragmented Whisper output into long continuous sentences.

Rules:
  - Drop pure filler responses (ค่ะ / ครับ / ใช่ / อ๋อ alone)
  - Merge everything in a "thought group" into one long sentence
  - A group ends when:
      • next chunk starts with "-" (speaker change marker), OR
      • time gap > 1.5 seconds

Re-slices audio for the merged chunks.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_AUDIO = ROOT / "audio-local"
PARENT = ROOT.parent
RAW_AUDIO_DIR = PARENT / "audio"

VIDEO_ID = "Nf-KbZ0XHMU"
GAP_THRESHOLD_SEC = 1.5
MAX_DURATION_SEC = 15.0

# Pure filler responses — single-token utterances with no content
FILLERS = {
    "ค่ะ", "ครับ", "คะ", "ครับๆ", "ค่ะๆ",
    "ใช่", "ใช่ค่ะ", "ใช่ครับ", "ใช่ ๆ", "ใช่ๆ", "ใช่ ๆ ค่ะ", "ใช่ ๆ ครับ",
    "อ๋อ", "อ้า", "เออ", "อืม", "เอ่อ",
    "โอเค", "ok", "OK",
    "นะ", "นะคะ", "นะครับ",
    "ครับ ๆ", "ค่ะ ๆ",
    "หรอ", "หรอครับ", "หรอคะ",
    "ใช่ไหม", "ใช่ไหมครับ", "ใช่ไหมคะ",
    "อืม ๆ", "เออ ๆ",
}


def normalize(s: str) -> str:
    """Strip dashes, whitespace for filler comparison."""
    return re.sub(r"\s+", " ", s.replace("-", "").strip()).strip()


def is_pure_filler(thai: str) -> bool:
    n = normalize(thai)
    if n in FILLERS:
        return True
    # Very short utterances (< 4 chars after normalization) likely fillers
    if len(n) < 4:
        return True
    return False


def starts_with_speaker_change(thai: str) -> bool:
    return thai.lstrip().startswith("-")


def merge_video(video_id: str):
    sentences_file = DATA / "sentences.json"
    sentences = json.loads(sentences_file.read_text())
    target = [s for s in sentences if s["video_id"] == video_id]
    other = [s for s in sentences if s["video_id"] != video_id]
    target.sort(key=lambda s: s["start"])

    print(f"  Input: {len(target)} fragmented sentences")

    # Step 1: filter pure fillers (but keep filler-only sentences if they
    # contain a speaker dash because that's a real conversational beat — we
    # still drop the text but preserve the time slot? Actually drop them.)
    cleaned = [s for s in target if not is_pure_filler(s["thai"])]
    print(f"  After filler removal: {len(cleaned)}")

    # Step 2: group into "thought blocks"
    # Break when: speaker change, gap > threshold, OR duration would exceed max.
    groups = []
    current = []
    prev_end = -100

    for s in cleaned:
        if not current:
            current = [s]
            prev_end = s["end"]
            continue
        gap = s["start"] - prev_end
        group_start = current[0]["start"]
        new_duration = s["end"] - group_start
        if (starts_with_speaker_change(s["thai"])
                or gap > GAP_THRESHOLD_SEC
                or new_duration > MAX_DURATION_SEC):
            groups.append(current)
            current = [s]
        else:
            current.append(s)
        prev_end = s["end"]

    if current:
        groups.append(current)

    print(f"  Merged into: {len(groups)} long sentences")

    # Step 3: build merged sentence objects
    merged = []
    for i, grp in enumerate(groups, start=1):
        thai = " ".join(s["thai"].strip() for s in grp)
        # Compact whitespace
        thai = re.sub(r"\s+", " ", thai).strip()
        sid = f"{video_id}_{i:04d}"
        merged.append({
            "id": sid,
            "video_id": video_id,
            "start": round(grp[0]["start"], 2),
            "end": round(grp[-1]["end"], 2),
            "thai": thai,
            "romanization": "",
            "translation": "",
            "vocab_ids": [],
            "annotations": [],
            "is_highlight": False,
            "audio_url": f"audio-local/{video_id}/{i:04d}.mp3",
        })

    # Step 4: write back
    new_sentences = other + merged
    sentences_file.write_text(json.dumps(new_sentences, ensure_ascii=False, indent=2))

    # Step 5: re-slice audio
    wav = RAW_AUDIO_DIR / f"{video_id}.wav"
    out_dir = SITE_AUDIO / video_id
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Slicing {len(merged)} audio clips…")
    for s in merged:
        idx = int(s["id"].rsplit("_", 1)[1])
        out_file = out_dir / f"{idx:04d}.mp3"
        start = max(0, s["start"] - 0.1)
        dur = (s["end"] - s["start"]) + 0.2
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(wav),
            "-ss", f"{start:.2f}", "-t", f"{dur:.2f}",
            "-c:a", "libmp3lame", "-b:a", "64k",
            str(out_file),
        ], check=True)

    # Update video metadata sentence count
    videos_file = DATA / "videos.json"
    videos = json.loads(videos_file.read_text())
    for v in videos:
        if v["id"] == video_id:
            v["sentence_count"] = len(merged)
    videos_file.write_text(json.dumps(videos, ensure_ascii=False, indent=2))

    # Stats
    durations = [s["end"] - s["start"] for s in merged]
    avg = sum(durations) / len(durations) if durations else 0
    print(f"  ✓ Avg sentence: {avg:.1f}s, max: {max(durations):.1f}s")
    return merged


if __name__ == "__main__":
    merge_video(VIDEO_ID)
    print("✅ Merge done. Now re-run enrich script to add annotations.")
