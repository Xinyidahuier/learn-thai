#!/usr/bin/env python3
"""
Auto-extract vocabulary from all articles and add to vocab.json.

Usage:
  python3 scripts/extract_vocab.py           # add words with freq >= 3
  python3 scripts/extract_vocab.py --min 2   # lower threshold
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Thai function words / stopwords to skip
STOPWORDS = {
    "ที่", "ว่า", "ไม่", "มัน", "คือ", "เรา", "ก็", "ครับ", "เป็น", "ใน",
    "มี", "ได้", "แล้ว", "ไป", "เลย", "เขา", "แต่", "ของ", "การ", "กับ",
    "ต้อง", "ใช่", "จะ", "มาก", "ไทย", "นี้", "และ", "อะไร", "แบบ", "ให้",
    "อยู่", "มา", "นะ", "กว่า", "แล้วก็", "ค่ะ", "คน", "อย่าง", "แต่ว่า",
    "ทำ", "พวก", "ขึ้น", "โดย", "เพื่อ", "แล้วก็", "เพราะ", "ถ้า", "หรือ",
    "ออก", "เอา", "ก่อน", "ก็คือ", "ด้วย", "จาก", "ซึ่ง", "แบบนี้", "นั้น",
    "ถึง", "บาง", "อีก", "ทุก", "เอง", "นั่น", "อยาก", "ต้องการ", "ทำให้",
    "สิ่ง", "สิ่งที่", "เรื่อง", "บอก", "พูด", "เห็น", "รู้", "คิด", "ลอง",
    "ยัง", "หลาย", "ใหม่", "ใหญ่", "เล็ก", "ดี", "เดียว", "นาน", "เลย",
    "แค่", "เกิน", "ส่วน", "เวลา", "ตอน", "วัน", "ปี", "คือว่า", "ก็ได้",
    "ทั้ง", "หมด", "ต่อ", "ตาม", "ใต้", "บน", "ใกล้", "ไกล", "ตรง",
    "อะ", "นะคะ", "นะครับ", "ค่ะๆ", "ครับๆ", "เออ", "อ้า", "อ๋อ",
    "เพราะว่า", "เพราะฉะนั้น", "ดังนั้น", "อย่างไรก็ตาม", "แน่นอน",
}

# Regex: keep only Thai-script tokens (skip English, numbers, punctuation)
THAI_RE = re.compile(r"^[\u0E00-\u0E7F]{3,}$")


def thai_id(word: str) -> str:
    h = hashlib.md5(word.encode()).hexdigest()[:6]
    return f"th_{h}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=3, help="minimum frequency")
    ap.add_argument("--article", help="only process this article_id")
    args = ap.parse_args()

    try:
        from pythainlp import word_tokenize
    except ImportError:
        print("Install pythainlp first: pip3 install pythainlp")
        return

    sentences_file = DATA / "sentences.json"
    vocab_file = DATA / "vocab.json"

    sents = json.loads(sentences_file.read_text())
    vocab = json.loads(vocab_file.read_text()) if vocab_file.exists() else []
    existing_words = {v["thai"] for v in vocab}

    if args.article:
        sents = [s for s in sents if s.get("article_id") == args.article]

    # Tokenize all Thai text
    print(f"Tokenizing {len(sents)} sentences…")
    counter = Counter()
    for s in sents:
        tokens = word_tokenize(s["thai"], engine="newmm")
        for t in tokens:
            t = t.strip()
            if THAI_RE.match(t) and t not in STOPWORDS:
                counter[t] += 1

    # Filter by frequency and not already in vocab
    candidates = [
        (word, freq)
        for word, freq in counter.most_common()
        if freq >= args.min and word not in existing_words
    ]

    print(f"Found {len(candidates)} new words with freq >= {args.min}")

    added = 0
    for word, freq in candidates:
        vocab.append({
            "id": thai_id(word),
            "thai": word,
            "romanization": "",
            "translation": "",
            "english": "",
            "part_of_speech": "",
            "frequency": freq,
            "tags": [],
        })
        added += 1

    vocab.sort(key=lambda v: -v.get("frequency", 0))
    vocab_file.write_text(json.dumps(vocab, ensure_ascii=False, indent=2))
    print(f"✅ Added {added} new words to vocab.json (total: {len(vocab)})")
    print()
    print("Top new words added:")
    for word, freq in candidates[:20]:
        print(f"  {word}  (×{freq})")


if __name__ == "__main__":
    main()
