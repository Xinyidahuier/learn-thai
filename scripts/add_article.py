#!/usr/bin/env python3
"""
Add a new article to Learn Thai. Supports 3 input types:

  # YouTube URL
  python3 scripts/add_article.py --url "https://youtube.com/watch?v=XXX" [--title "..."]

  # Local audio file (mp3 / wav / m4a)
  python3 scripts/add_article.py --audio path/to/file.mp3 --title "..."

  # Pure Thai text (no audio)
  python3 scripts/add_article.py --text path/to/file.txt --title "..."

Pipeline:
  1. (For YouTube/audio) Transcribe with Whisper large-v3 + prompt + --translate
  2. Merge fragmented sentences into coherent chunks (<=15 s each)
  3. Slice audio into per-sentence MP3 clips
  4. Scan for vocab matches and annotate
  5. Append to data/articles.json + data/sentences.json
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_AUDIO = ROOT / "audio-local"
PARENT = ROOT.parent
RAW_AUDIO_DIR = PARENT / "audio"
TRANSCRIPTS = PARENT / "transcripts"
MODEL = PARENT / "models" / "ggml-large-v3.bin"

# Initial prompt for Whisper — primes proper nouns and common business terms
WHISPER_PROMPT = (
    "ราวิภา Ravipa Disney Infinity Collection Collab Mickey Stitch Zootopia "
    "แบรนด์ ดีไซน์ ดีไซเนอร์ สาขา ต่างประเทศ โกลบอล global Brand Design "
    "บุกเบิก กรุยทาง OEM SME ท้าวความ ฮ่องกง Macau Japan Shinjuku "
    "ลูกค้า End user Intellectual Property IP Value "
    "Style Guide Manual Book Adapt think beyond make it different "
    "Selling Point Positioning Exclusive Lifestyle Quality Innovation"
)

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

GAP_THRESHOLD_SEC = 1.5
MAX_DURATION_SEC = 15.0


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def slugify(s: str, max_len: int = 24) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip()).strip("-")
    return s[:max_len].lower() or "article"


def unique_id(seed: str) -> str:
    h = hashlib.md5(seed.encode()).hexdigest()[:8]
    return f"{slugify(seed)}-{h}"


def youtube_id(url: str) -> "str | None":
    p = urlparse(url)
    if p.hostname == "youtu.be":
        return p.path.lstrip("/")
    qs = parse_qs(p.query)
    return qs.get("v", [None])[0]


def audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def to_16k_wav(src: Path, dst: Path):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(dst),
    ], check=True)


# ---------------------------------------------------------------------------
# Whisper transcription (runs twice: Thai + English translation)
# ---------------------------------------------------------------------------

SRT_BLOCK_RE = re.compile(
    r"(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\n((?:.+\n?)+)",
    re.MULTILINE,
)


def parse_srt(srt_path: Path):
    text = srt_path.read_bytes().decode("utf-8", errors="ignore")
    blocks = []
    for m in SRT_BLOCK_RE.finditer(text):
        idx = int(m.group(1))
        start = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4)) + int(m.group(5)) / 1000
        end   = int(m.group(6)) * 3600 + int(m.group(7)) * 60 + int(m.group(8)) + int(m.group(9)) / 1000
        text_block = m.group(10).strip()
        if not text_block:
            continue
        if text_block.startswith("[") and text_block.endswith("]"):
            continue
        blocks.append({"idx": idx, "start": start, "end": end, "text": text_block})
    return blocks


def transcribe(wav: Path, article_id: str, translate: bool) -> Path:
    """Run whisper-cli. `translate=True` yields English instead of Thai."""
    suffix = "en" if translate else "th"
    out_base = TRANSCRIPTS / f"{article_id}_{suffix}"
    srt = out_base.with_suffix(".srt")
    if srt.exists():
        return srt
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    cmd = [
        "whisper-cli", "-m", str(MODEL), "-f", str(wav),
        "-l", "th", "-otxt", "-osrt", "-of", str(out_base),
        "--suppress-nst", "-mc", "0",
        "--prompt", WHISPER_PROMPT,
    ]
    if translate:
        cmd.append("-tr")
    print(f"  ↳ transcribing ({'en' if translate else 'th'}) — this may take a while…")
    subprocess.run(cmd, check=True)
    return srt


# ---------------------------------------------------------------------------
# Merging short Whisper fragments into coherent chunks
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("-", "").strip()).strip()


def is_pure_filler(thai: str) -> bool:
    n = normalize(thai)
    return n in FILLERS or len(n) < 4


def starts_with_speaker_change(thai: str) -> bool:
    return thai.lstrip().startswith("-")


def merge_blocks(blocks):
    cleaned = [b for b in blocks if not is_pure_filler(b["text"])]
    groups, current, prev_end = [], [], -100
    for s in cleaned:
        if not current:
            current = [s]; prev_end = s["end"]; continue
        gap = s["start"] - prev_end
        duration = s["end"] - current[0]["start"]
        if (starts_with_speaker_change(s["text"])
                or gap > GAP_THRESHOLD_SEC
                or duration > MAX_DURATION_SEC):
            groups.append(current); current = [s]
        else:
            current.append(s)
        prev_end = s["end"]
    if current:
        groups.append(current)
    merged = []
    for i, grp in enumerate(groups, start=1):
        text = re.sub(r"\s+", " ", " ".join(x["text"].strip() for x in grp)).strip()
        merged.append({
            "idx": i,
            "start": round(grp[0]["start"], 2),
            "end": round(grp[-1]["end"], 2),
            "text": text,
        })
    return merged


def merge_with_translation(th_blocks, en_blocks):
    """Merge thai blocks, then align english blocks by time overlap."""
    thai_merged = merge_blocks(th_blocks)
    for m in thai_merged:
        overlapping = [b for b in en_blocks if b["end"] > m["start"] and b["start"] < m["end"]]
        en_text = re.sub(r"\s+", " ", " ".join(b["text"].strip() for b in overlapping)).strip()
        m["english"] = en_text
    return thai_merged


# ---------------------------------------------------------------------------
# Audio slicing
# ---------------------------------------------------------------------------

def slice_audio(wav: Path, article_id: str, sentences):
    out_dir = SITE_AUDIO / article_id
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ↳ slicing {len(sentences)} audio clips…")
    for s in sentences:
        idx = int(s["id"].rsplit("_", 1)[1])
        out_file = out_dir / f"{idx:04d}.mp3"
        start = max(0, s["start"] - 0.1)
        dur = (s["end"] - s["start"]) + 0.2
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
            "-ss", f"{start:.2f}", "-t", f"{dur:.2f}",
            "-c:a", "libmp3lame", "-b:a", "64k", str(out_file),
        ], check=True)


# ---------------------------------------------------------------------------
# Vocab annotation (scans existing vocab.json)
# ---------------------------------------------------------------------------

def annotate_sentences(sentences):
    vocab_file = DATA / "vocab.json"
    if not vocab_file.exists():
        return
    vocab = json.loads(vocab_file.read_text())
    # Reset freq counts before recounting
    for v in vocab:
        v.setdefault("frequency", 0)

    for s in sentences:
        annotations = []
        for v in vocab:
            needle = v["thai"]
            if not needle:
                continue
            start = 0
            while True:
                idx = s["thai"].find(needle, start)
                if idx == -1:
                    break
                annotations.append({"start": idx, "end": idx + len(needle), "vocab_id": v["id"]})
                v["frequency"] += 1
                start = idx + 1
        # De-overlap
        annotations.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        merged = []
        last_end = -1
        for a in annotations:
            if a["start"] >= last_end:
                merged.append(a); last_end = a["end"]
        s["annotations"] = merged

    vocab.sort(key=lambda v: -v.get("frequency", 0))
    vocab_file.write_text(json.dumps(vocab, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Article registry updates
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Vocab expansion — extract new words from article, translate, re-annotate
# ---------------------------------------------------------------------------

THAI_TOKEN_RE = re.compile(r"^[\u0E00-\u0E7F]{3,}$")

STOPWORDS = {
    "ที่", "ว่า", "ไม่", "มัน", "คือ", "เรา", "ก็", "ครับ", "เป็น", "ใน",
    "มี", "ได้", "แล้ว", "ไป", "เลย", "เขา", "แต่", "ของ", "การ", "กับ",
    "ต้อง", "ใช่", "จะ", "มาก", "นี้", "และ", "อะไร", "แบบ", "ให้",
    "อยู่", "มา", "นะ", "กว่า", "แล้วก็", "ค่ะ", "คน", "อย่าง", "แต่ว่า",
    "ทำ", "พวก", "ขึ้น", "โดย", "เพื่อ", "เพราะ", "ถ้า", "หรือ",
    "ออก", "เอา", "ก่อน", "ก็คือ", "ด้วย", "จาก", "ซึ่ง", "แบบนี้", "นั้น",
    "ถึง", "บาง", "อีก", "ทุก", "เอง", "นั่น", "อยาก", "ต้องการ", "ทำให้",
    "สิ่ง", "สิ่งที่", "เรื่อง", "บอก", "พูด", "เห็น", "รู้", "คิด",
    "ยัง", "หลาย", "เดียว", "เลย", "แค่", "ส่วน", "เวลา", "ตอน", "วัน",
    "ปี", "ก็ได้", "ทั้ง", "หมด", "ต่อ", "ตาม", "อะ", "นะคะ", "นะครับ",
    "เพราะว่า", "เพราะฉะนั้น", "ดังนั้น", "แน่นอน", "ไทย",
}


def _vocab_id(word: str) -> str:
    return "th_" + hashlib.md5(word.encode()).hexdigest()[:6]


def expand_vocab(article_id: str, min_freq: int = 2):
    try:
        from pythainlp import word_tokenize
    except ImportError:
        print("  ↳ pythainlp not found, skipping vocab expansion")
        return

    sentences_file = DATA / "sentences.json"
    vocab_file = DATA / "vocab.json"
    sents = json.loads(sentences_file.read_text())
    vocab = json.loads(vocab_file.read_text()) if vocab_file.exists() else []
    existing = {v["thai"] for v in vocab}

    # Count tokens in the new article only
    article_sents = [s for s in sents if s.get("article_id") == article_id]
    from collections import Counter
    counter = Counter()
    for s in article_sents:
        for t in word_tokenize(s["thai"], engine="newmm"):
            t = t.strip()
            if THAI_TOKEN_RE.match(t) and t not in STOPWORDS:
                counter[t] += 1

    new_words = [(w, f) for w, f in counter.most_common() if f >= min_freq and w not in existing]
    if not new_words:
        print("  ↳ no new vocab to add")
        return

    print(f"  ↳ translating {len(new_words)} new words…")
    try:
        import warnings; warnings.filterwarnings("ignore")
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="th", target="en")
        batch_size = 20
        translations: dict[str, str] = {}
        for i in range(0, len(new_words), batch_size):
            batch = new_words[i:i + batch_size]
            try:
                result = translator.translate("\n".join(w for w, _ in batch))
                parts = result.split("\n")
                for j, (word, _) in enumerate(batch):
                    if j < len(parts) and parts[j].strip():
                        translations[word] = parts[j].strip()
            except Exception:
                pass
            time.sleep(0.3)
    except ImportError:
        print("  ↳ deep-translator not found, adding words without translation")
        translations = {}

    for word, freq in new_words:
        vocab.append({
            "id": _vocab_id(word),
            "thai": word,
            "romanization": "",
            "translation": "",
            "english": translations.get(word, ""),
            "part_of_speech": "",
            "frequency": freq,
            "tags": [],
        })

    # Re-annotate all sentences with updated vocab
    for v in vocab:
        v["frequency"] = 0
    for s in sents:
        anns = []
        for v in vocab:
            needle = v["thai"]
            if not needle:
                continue
            start = 0
            while True:
                idx = s["thai"].find(needle, start)
                if idx == -1:
                    break
                anns.append({"start": idx, "end": idx + len(needle), "vocab_id": v["id"]})
                v["frequency"] += 1
                start = idx + 1
        anns.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        merged, last_end = [], -1
        for a in anns:
            if a["start"] >= last_end:
                merged.append(a); last_end = a["end"]
        s["annotations"] = merged

    vocab.sort(key=lambda v: -v.get("frequency", 0))
    vocab_file.write_text(json.dumps(vocab, ensure_ascii=False, indent=2))
    sentences_file.write_text(json.dumps(sents, ensure_ascii=False, indent=2))
    print(f"  ↳ vocab: +{len(new_words)} words (total {len(vocab)}), all sentences re-annotated")


# ---------------------------------------------------------------------------

def save_article(article, sentences):
    articles_file = DATA / "articles.json"
    sentences_file = DATA / "sentences.json"
    articles = json.loads(articles_file.read_text()) if articles_file.exists() else []
    all_sents = json.loads(sentences_file.read_text()) if sentences_file.exists() else []
    articles = [a for a in articles if a["id"] != article["id"]]
    all_sents = [s for s in all_sents if (s.get("article_id") or s.get("video_id")) != article["id"]]
    articles.append(article)
    all_sents.extend(sentences)
    articles_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    sentences_file.write_text(json.dumps(all_sents, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Input adapters
# ---------------------------------------------------------------------------

def process_from_audio(wav: Path, article_id: str, title: str, source_url: str, atype: str):
    th_srt = transcribe(wav, article_id, translate=False)
    en_srt = transcribe(wav, article_id, translate=True)
    th_blocks = parse_srt(th_srt)
    en_blocks = parse_srt(en_srt)
    merged = merge_with_translation(th_blocks, en_blocks)
    if not merged:
        print("⚠️  No content parsed"); sys.exit(1)

    sentences = []
    for m in merged:
        sid = f"{article_id}_{m['idx']:04d}"
        sentences.append({
            "id": sid,
            "article_id": article_id,
            "start": m["start"],
            "end": m["end"],
            "thai": m["text"],
            "translation": "",          # Chinese — fill in manually or ask Claude
            "english": m.get("english", ""),
            "romanization": "",
            "vocab_ids": [],
            "annotations": [],
            "is_highlight": False,
            "audio_url": f"audio-local/{article_id}/{m['idx']:04d}.mp3",
        })

    slice_audio(wav, article_id, sentences)
    annotate_sentences(sentences)

    duration = audio_duration(wav)
    article = {
        "id": article_id,
        "title": title,
        "type": atype,
        "source_url": source_url,
        "duration_sec": duration,
        "duration_str": f"{int(duration // 60)}:{int(duration % 60):02d}",
        "sentence_count": len(sentences),
        "status": "studying",
        "favorite": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_article(article, sentences)
    print(f"✅ Added article: {article_id} — {len(sentences)} sentences")

    # Clean up raw audio to save disk space (sliced clips are already in audio-local/)
    for p in [wav, wav.with_suffix(".mp3")]:
        if p.exists():
            p.unlink()
            print(f"  ↳ deleted {p.name}")

    expand_vocab(article_id)


def process_youtube(url: str, title: "str | None"):
    vid = youtube_id(url)
    if not vid:
        print(f"Could not parse YouTube URL"); sys.exit(1)
    article_id = vid
    RAW_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    wav = RAW_AUDIO_DIR / f"{article_id}.wav"
    mp3 = RAW_AUDIO_DIR / f"{article_id}.mp3"
    if not wav.exists():
        if not mp3.exists():
            print(f"  ↳ downloading audio…")
            subprocess.run([
                "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                "-o", str(RAW_AUDIO_DIR / "%(id)s.%(ext)s"), url,
            ], check=True)
        print(f"  ↳ converting to 16kHz wav…")
        to_16k_wav(mp3, wav)
    if not title:
        r = subprocess.run(["yt-dlp", "--get-title", url],
                           capture_output=True, text=True, check=True)
        title = r.stdout.strip().splitlines()[-1]
    process_from_audio(wav, article_id, title, url, "youtube")


def process_audio_file(path: Path, title: str):
    src = path.resolve()
    if not src.exists():
        print(f"File not found: {src}"); sys.exit(1)
    article_id = unique_id(title or src.stem)
    RAW_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    wav = RAW_AUDIO_DIR / f"{article_id}.wav"
    if not wav.exists():
        print(f"  ↳ converting to 16kHz wav…")
        to_16k_wav(src, wav)
    process_from_audio(wav, article_id, title, f"file://{src}", "audio")


def process_text_file(path: Path, title: str, audio_path):
    src = path.resolve()
    if not src.exists():
        print(f"File not found: {src}"); sys.exit(1)
    article_id = unique_id(title or src.stem)

    # If audio is provided, fall through to audio pipeline (text will be overwritten by whisper)
    if audio_path:
        print("⚠️  --audio given; text file ignored in favour of whisper output")
        process_audio_file(audio_path, title)
        return

    # Pure text path — split by newlines / Thai sentence markers
    text = src.read_text(encoding="utf-8").strip()
    # Split by blank lines or Thai punctuation (., ?, !, or end markers)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=[\.\?\!])\s+", text) if p.strip()]

    sentences = []
    for i, p in enumerate(paragraphs, start=1):
        sid = f"{article_id}_{i:04d}"
        sentences.append({
            "id": sid,
            "article_id": article_id,
            "start": 0,
            "end": 0,
            "thai": p,
            "translation": "",
            "english": "",
            "romanization": "",
            "vocab_ids": [],
            "annotations": [],
            "is_highlight": False,
            "audio_url": "",
        })

    annotate_sentences(sentences)
    article = {
        "id": article_id,
        "title": title,
        "type": "text",
        "source_url": f"file://{src}",
        "duration_sec": 0,
        "duration_str": "",
        "sentence_count": len(sentences),
        "status": "studying",
        "favorite": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_article(article, sentences)
    print(f"✅ Added text article: {article_id} — {len(sentences)} paragraphs")
    expand_vocab(article_id)


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="YouTube URL")
    g.add_argument("--audio", help="Local audio file path")
    g.add_argument("--text", help="Thai text file path")
    ap.add_argument("--title", help="Article title (required for audio/text)")
    ap.add_argument("--audio-with-text", help="Optional audio to pair with --text")
    args = ap.parse_args()

    if args.url:
        process_youtube(args.url, args.title)
    elif args.audio:
        if not args.title:
            print("--title required for audio input"); sys.exit(1)
        process_audio_file(Path(args.audio), args.title)
    elif args.text:
        if not args.title:
            print("--title required for text input"); sys.exit(1)
        audio = Path(args.audio_with_text) if args.audio_with_text else None
        process_text_file(Path(args.text), args.title, audio)


if __name__ == "__main__":
    main()
