#!/usr/bin/env python3
"""
Process a YouTube video into Learn Thai data.

Usage:
  python3 scripts/process_video.py <youtube_url> [--title "Optional Title"]

Pipeline:
  1. Download audio (yt-dlp) → ../audio/<id>.wav
  2. Transcribe (whisper-cli) → ../transcripts/<id>.srt
  3. Parse SRT into sentences
  4. Slice each sentence into a small MP3 (ffmpeg) → audio-local/<id>/<n>.mp3
  5. Append to data/sentences.json + data/videos.json

Note: this only handles transcription + slicing.
Vocab extraction + romanization + translation are added in a second step.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "data"
SITE_AUDIO = ROOT / "audio-local"
PARENT = ROOT.parent  # /Users/xinyi/学习/Thai
RAW_AUDIO = PARENT / "audio"
TRANSCRIPTS = PARENT / "transcripts"
MODEL = PARENT / "models" / "ggml-medium.bin"

WHISPER_FLAGS = ["--suppress-nst", "-mc", "0"]


def get_video_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    p = urlparse(url)
    if p.hostname in ("youtu.be",):
        return p.path.lstrip("/")
    qs = parse_qs(p.query)
    if "v" in qs:
        return qs["v"][0]
    raise ValueError(f"Could not extract video id from {url}")


def download_audio(url: str, vid: str) -> Path:
    out_mp3 = RAW_AUDIO / f"{vid}.mp3"
    out_wav = RAW_AUDIO / f"{vid}.wav"
    if out_wav.exists():
        print(f"  ↳ wav exists, skipping download")
        return out_wav

    RAW_AUDIO.mkdir(parents=True, exist_ok=True)
    if not out_mp3.exists():
        print(f"  ↳ downloading audio…")
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", str(RAW_AUDIO / "%(id)s.%(ext)s"), url,
        ], check=True)

    print(f"  ↳ converting to 16kHz wav…")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(out_mp3),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav),
    ], check=True, capture_output=True)
    return out_wav


def transcribe(wav: Path, vid: str) -> Path:
    out_base = TRANSCRIPTS / f"{vid}_v2"
    srt = out_base.with_suffix(".srt")
    if srt.exists():
        print(f"  ↳ transcript exists, skipping")
        return srt
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    print(f"  ↳ transcribing (this can take 10-30 min)…")
    subprocess.run([
        "whisper-cli", "-m", str(MODEL), "-f", str(wav),
        "-l", "th", "-otxt", "-osrt", "-of", str(out_base),
        *WHISPER_FLAGS,
    ], check=True)
    return srt


SRT_BLOCK_RE = re.compile(
    r"(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\n((?:.+\n?)+)",
    re.MULTILINE,
)


def parse_srt(srt_path: Path):
    # Whisper sometimes produces invalid UTF-8 bytes; ignore them
    text = srt_path.read_bytes().decode("utf-8", errors="ignore")
    blocks = []
    for m in SRT_BLOCK_RE.finditer(text):
        idx = int(m.group(1))
        start = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4)) + int(m.group(5)) / 1000
        end   = int(m.group(6)) * 3600 + int(m.group(7)) * 60 + int(m.group(8)) + int(m.group(9)) / 1000
        text_block = m.group(10).strip()
        if not text_block:
            continue
        # Filter out music/sound markers
        if text_block.startswith("[") and text_block.endswith("]"):
            continue
        blocks.append({"idx": idx, "start": start, "end": end, "thai": text_block})
    return blocks


def slice_audio(wav: Path, vid: str, blocks):
    out_dir = SITE_AUDIO / vid
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ↳ slicing {len(blocks)} sentences…")
    for b in blocks:
        out_file = out_dir / f"{b['idx']:04d}.mp3"
        if out_file.exists():
            continue
        # Add small padding
        start = max(0, b["start"] - 0.1)
        dur = (b["end"] - b["start"]) + 0.2
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(wav),
            "-ss", f"{start:.2f}", "-t", f"{dur:.2f}",
            "-c:a", "libmp3lame", "-b:a", "64k",
            str(out_file),
        ], check=True)
        b["audio_relpath"] = f"audio-local/{vid}/{b['idx']:04d}.mp3"
    return blocks


def update_data(vid: str, title: str, url: str, blocks, duration: float):
    SITE_DATA.mkdir(parents=True, exist_ok=True)

    videos_file = SITE_DATA / "videos.json"
    sentences_file = SITE_DATA / "sentences.json"

    videos = json.loads(videos_file.read_text()) if videos_file.exists() else []
    sentences = json.loads(sentences_file.read_text()) if sentences_file.exists() else []

    # Replace any existing entry for this video
    videos = [v for v in videos if v.get("id") != vid]
    sentences = [s for s in sentences if s.get("video_id") != vid]

    videos.append({
        "id": vid,
        "title": title,
        "url": url,
        "duration_sec": duration,
        "duration_str": f"{int(duration // 60)}:{int(duration % 60):02d}",
        "sentence_count": len(blocks),
    })

    for b in blocks:
        sid = f"{vid}_{b['idx']:04d}"
        sentences.append({
            "id": sid,
            "video_id": vid,
            "start": round(b["start"], 2),
            "end": round(b["end"], 2),
            "thai": b["thai"],
            "romanization": "",   # filled in step 2
            "translation": "",    # filled in step 2
            "vocab_ids": [],
            "audio_url": b.get("audio_relpath", ""),
        })

    videos_file.write_text(json.dumps(videos, ensure_ascii=False, indent=2))
    sentences_file.write_text(json.dumps(sentences, ensure_ascii=False, indent=2))
    print(f"  ↳ wrote {len(blocks)} sentences to data/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--title", default=None, help="Optional video title")
    args = ap.parse_args()

    vid = get_video_id(args.url)
    title = args.title or vid
    print(f"Processing {vid} — {title}")

    wav = download_audio(args.url, vid)
    srt = transcribe(wav, vid)
    blocks = parse_srt(srt)
    print(f"  ↳ parsed {len(blocks)} non-music sentences")

    if not blocks:
        print("⚠️  No sentences extracted (transcription may have failed)")
        sys.exit(1)

    blocks = slice_audio(wav, vid, blocks)
    duration = blocks[-1]["end"] if blocks else 0
    update_data(vid, title, args.url, blocks, duration)
    print(f"✅ Done. Next: enrich with romanization + translation + vocab.")


if __name__ == "__main__":
    main()
