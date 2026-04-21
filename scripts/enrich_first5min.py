#!/usr/bin/env python3
"""
Enrich the first 5 minutes (now 15 merged sentences) with:
- Business vocab entries (hand-curated dictionary)
- Word-level annotations (positions of vocab in each sentence)
- Translations for each merged paragraph
- is_highlight flag for paragraphs heavy in business content

Usage: python3 scripts/enrich_first5min.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VIDEO_ID = "Nf-KbZ0XHMU"
CUTOFF_SEC = 300

# ---------------------------------------------------------------------------
# Vocabulary bank — business / professional terms.
# ---------------------------------------------------------------------------
VOCAB = [
    ("v_botrian",      "บทเรียน",         "bòt-rian",              "经验教训 (lesson)",                          "n.",  ["business", "general"]),
    ("v_senthaang",    "เส้นทาง",         "sên-thaang",            "路径、历程 (path, journey)",                 "n.",  ["business"]),
    ("v_təəptoo",      "เติบโต",          "təə̀p-too",             "成长、发展 (to grow)",                       "v.",  ["business"]),
    ("v_saangbraen",   "สร้างแบรนด์",     "sâang braen",           "打造品牌 (build a brand)",                   "v.",  ["business", "marketing"]),
    ("v_braen",        "แบรนด์",          "braen",                 "品牌 (brand)",                               "n.",  ["business", "marketing"]),
    ("v_prasopsamret", "ประสบความสำเร็จ", "prà-sòp khwaam-sǎm-rèt","成功、取得成就 (to succeed)",                 "v.",  ["business"]),
    ("v_ongkɔɔn",      "องค์กร",          "ong-kɔɔn",              "组织、机构 (organization)",                  "n.",  ["business", "corporate"]),
    ("v_khayaai",      "ขยาย",            "khà-yǎai",              "扩张、扩大 (to expand)",                     "v.",  ["business"]),
    ("v_yɔɔmpɛɛ",      "ยอมแพ้",          "yɔɔm-pɛ́ɛ",             "放弃、认输 (to give up)",                    "v.",  ["general"]),
    ("v_prathet",      "ประเทศ",          "prà-thêet",             "国家 (country)",                             "n.",  ["general"]),
    ("v_jiwənrii",     "จิวเวลรี่",       "jiu-wəl-rîi",           "珠宝 (jewelry) — loanword",                  "n.",  ["business", "industry"]),
    ("v_oem",          "OEM",             "oo-ii-em",              "代工生产 (Original Equipment Manufacturing)", "n.",  ["business", "industry"]),
    ("v_phalit",       "ผลิต",            "phà-lìt",               "生产、制造 (to produce, manufacture)",        "v.",  ["business", "industry"]),
    ("v_waeluu",       "แวลู",            "wɛɛ-luu",               "价值 (value) — loanword",                    "n.",  ["business"]),
    ("v_ip",           "intellectual property", "in-ter-lék-chuân prɔ́ɔ-pəə-tîi", "知识产权 (IP)",            "n.",  ["business", "legal"]),
    ("v_diisai",       "ดีไซน์",          "dii-sai",               "设计 (design) — loanword",                   "n.",  ["business", "marketing"]),
    ("v_diisainəə",    "ดีไซเนอร์",       "dii-sai-nəə",           "设计师 (designer)",                          "n.",  ["business"]),
    ("v_design",       "design",          "dii-sai",               "设计 (design)",                              "n.",  ["business"]),
    ("v_enduser",      "End user",        "en-yuu-sə̂ə",           "终端用户 (end user)",                        "n.",  ["business"]),
    ("v_bukbəək",      "บุกเบิก",         "bùk-bə̀ək",             "开拓、开创 (to pioneer)",                    "v.",  ["business"]),
    ("v_kruithaang",   "กรุยทาง",         "krui-thaang",           "开路、铺路 (to pave the way)",               "v.",  ["business", "idiom"]),
    ("v_global",       "global",          "glôo-bɔɔn",             "全球的 (global) — loanword",                 "adj.",["business"]),
    ("v_saakha",       "สาขา",            "sǎa-khǎa",              "分店、分公司 (branch)",                      "n.",  ["business"]),
    ("v_tangprathet",  "ต่างประเทศ",      "tàang prà-thêet",       "国外、海外 (foreign countries, abroad)",     "n.",  ["business"]),
    ("v_online",       "ออไลน์",          "ɔɔn-lai",               "线上 (online) — loanword",                   "adj.",["business", "marketing"]),
    ("v_popup",        "ป๊อปอัป",         "pɔ́p-àp",               "快闪店 (pop-up store)",                      "n.",  ["business", "marketing"]),
    ("v_luukkhaa",     "ลูกค้า",          "lûuk-kháa",             "顾客、客户 (customer)",                      "n.",  ["business"]),
    ("v_patjai",       "ปัจจัย",          "pàt-jai",               "因素、要素 (factor)",                        "n.",  ["general"]),
    ("v_raangwan",     "รางวัล",          "raang-wan",             "奖项、奖励 (award, prize)",                  "n.",  ["general", "business"]),
    ("v_tɔɔyɔɔt",      "ต่อยอด",          "tɔ̀ɔ-yɔ̂ɔt",            "延展、扩展 (to build upon, extend)",          "v.",  ["business", "idiom"]),
    ("v_khwaammaai",   "ความหมาย",        "khwaam-mǎai",           "含义、意义 (meaning)",                       "n.",  ["general"]),
    ("v_khɔɔngkhwan",  "ของขวัญ",         "khɔ̌ɔng-khwǎn",         "礼物 (gift)",                                "n.",  ["general"]),
    ("v_ig",           "ไอจี",            "ai-jii",                "Instagram — loanword",                       "n.",  ["marketing", "social"]),
    ("v_khunnaphaap",  "คุณภาพ",          "khun-na-phâap",         "质量、品质 (quality)",                        "n.",  ["business"]),
    ("v_ookaat",       "โอกาส",           "oo-kàat",               "机会 (opportunity)",                         "n.",  ["business"]),
    ("v_collab",       "Collab",          "khɔɔn-lɛ̂ɛp",           "合作 (collaboration) — loanword",            "n.",  ["business", "marketing"]),
    ("v_collection",   "Collection",      "khɔɔn-lék-chân",        "系列 (collection) — loanword",               "n.",  ["business", "marketing"]),
    ("v_disney",       "Disney",          "dít-nîi",               "迪士尼 (Disney)",                            "n.",  ["business", "brand"]),
    ("v_thurakit",     "Joy หรือ Collab", "Joy rʉ̌ʉ Collab",       "联名或合作 (Joint or Collab)",                "n.",  ["business", "marketing"]),
]

# ---------------------------------------------------------------------------
# Translations + highlight flags, keyed by 4-digit sentence index.
# (Indices come from the merged sentences.json.)
# ---------------------------------------------------------------------------
ENRICHMENT = {
    "0001": {"trans": "我们来聊聊这些经验教训，或者说成长之路上的种种。先讲讲必须要付出的代价比较好——走到今天这一步。", "highlight": True},
    "0002": {"trans": "这位（嘉宾）是个特别的人。我理解把品牌做到这个规模并非只有收获——必然有我们要付出的代价。", "highlight": True},
    "0003": {"trans": "很多人可能会说我们多么成功，但 Sa 说：没人知道我们有多累。真的非常累。就像——我们越成长，组织越大，扩张越多，挑战就越难。", "highlight": True},
    "0004": {"trans": "虽然很难，但我们不要向它投降。这是 Sa 每天对自己说的话：「如果容易，所有人都去做了。」然后告诉自己：「旧的钥匙，打不开新家的门。」", "highlight": True},
    "0005": {"trans": "大家好，我是 Khen Nakharin，这里是 The Secret Sauce.", "highlight": False},
    "0006": {"trans": "由 Ravipa 赞助播出。", "highlight": False},
    "0007": {"trans": "大家好，我是 Khen Nakharin，这里是 The Secret Sauce.", "highlight": False},
    "0008": {"trans": "由 Ravipa 赞助。我必须先做个铺垫，让大家明白——", "highlight": False},
    "0009": {"trans": "泰国一直以珠宝业闻名，但我感觉大部分都是 OEM（代工）——我们为世界各大品牌代工生产。", "highlight": True},
    "0010": {"trans": "但 Ravipa 这个品牌处在价值链最高端的位置。", "highlight": True},
    "0011": {"trans": "哇，不敢轻易尝试啊！", "highlight": False},
    "0012": {"trans": "哇，不敢这么解释吗？意思是……", "highlight": False},
    "0013": {"trans": "思想的价值，对吧？知识产权（IP）——设计的价值。然后是真正拥有品牌、面向 End User（终端用户，即普通消费者）。我很幸运能从最早期就看到 Sa 创业。", "highlight": True},
    "0014": {"trans": "应该是疫情后初期，那时 Moo 系列开始走红。再后来一个阶段，是 Sa 开始与 Disney 这类品牌合作（Joint / Collab）——是泰国最早一批做的人。但今天还有更好的消息。", "highlight": True},
    "0015": {"trans": "作为能把这个故事传达给所有人的人我很高兴——大家能得到宝贵的经验教训：Sa 是开拓者、是铺路人，今天她的品牌是——", "highlight": True},
    "0016": {"trans": "——真正全球化（Global）的珠宝品牌。所以想先问：今天 Ravipa 处在什么阶段了？——好的。从那天起，（Ravipa）是一个线上（online）品牌……", "highlight": True},
    "0017": {"trans": "小小的 pop-up 店，跟姐姐两个人亲自去卖、自己收摊。到今天已经有约 40 家分店了——泰国有，也有海外。目前在 3 个海外国家。", "highlight": True},
    "0018": {"trans": "有澳门、日本，还有香港 2 家。——刚才说海外 3 家主要在哪里？——在澳门，是 Galeries Lafayette（老佛爷百货）。", "highlight": True},
    "0019": {"trans": "哦，是巴黎那家大百货的（澳门分店）！然后——日本店在 Disney Store Japan，就在新宿。再两家是香港 K11 Musea 和 Harbour City。", "highlight": True},
    "0020": {"trans": "都开在真正的全球地标位置。说到「国外」这个词——今天「Global」在你 Sa 心目中的含义是什么？——我认为「全球化」就是被更多人喜爱，不只是在泰国有客户。", "highlight": True},
    "0021": {"trans": "不只是泰国人，而是客户遍及海外。今天想聊聊：是怎么走到这个层次的？从我最早看到你的那一天起——简单总结一下走过的路，到今天这个全球化阶段。", "highlight": True},
    "0022": {"trans": "你觉得有哪些因素，让你走到了今天这一步？", "highlight": True},
    "0023": {"trans": "我跟姐姐是从设计珠宝起步的。我们是珠宝设计领域获奖很多的品牌——从一个小小的设计师（designer）品牌开始，赢了许多奖，把奖金不断延展投入业务。", "highlight": True},
    "0024": {"trans": "Ravipa 的珠宝必须是真能戴的、每天都能戴，并且要有意义。如果只是好看的珠宝实在太多了——我们必须做出能真正每天佩戴的珠宝，里面蕴含意义、积极、幸运的元素，让顾客觉得想买来送给自己。", "highlight": True},
    "0025": {"trans": "是送给自己庆祝某事的 gift，也是送给心爱之人的 gift。但「有意义（meaningful）」这个词范围太广了……其中一个真正击中人心的，就是「幸运（Lucky）」这个词。", "highlight": True},
    "0026": {"trans": "那么，我能请你举几个例子吗？我会从最早期开始介绍。我的团队已经准备好了，举三个时期为例。", "highlight": False},
    "0027": {"trans": "对吧，这样我们就能看到——好的。", "highlight": False},
    "0028": {"trans": "「I believe it.」听众朋友们谢谢大家——你们会看到第一个时期。对自己来说，比如那些在 IG 上做小生意的年轻人，让他们看到这里有 know-how。因为这（Ravipa）应该是 IG 最早一批的开拓者——对，IG 刚兴起就开始做了。", "highlight": True},
    "0029": {"trans": "然后在 K Village 那种地方卖，对吧？", "highlight": False},
    "0030": {"trans": "我记得！记得出 booth 的样子，我有照片，待会儿放图，我能看到画面——因为这真的就是起点，第一个 Collection，就是这一个 Collection。", "highlight": True},
}


def find_positions(thai_text: str, needle: str):
    positions = []
    start = 0
    while True:
        idx = thai_text.find(needle, start)
        if idx == -1:
            break
        positions.append((idx, idx + len(needle)))
        start = idx + 1
    return positions


def enrich():
    sentences = json.loads((DATA / "sentences.json").read_text())

    # vocab.json — overwrite with the curated bank
    vocab_objs = []
    vocab_freq = {}
    for vid, thai, rom, trans, pos, tags in VOCAB:
        vocab_objs.append({
            "id": vid,
            "thai": thai,
            "romanization": rom,
            "translation": trans,
            "part_of_speech": pos,
            "tags": tags,
            "frequency": 0,
        })
        vocab_freq[vid] = 0

    # Enrich first 5 min sentences
    for s in sentences:
        if s["video_id"] != VIDEO_ID:
            continue
        if s["start"] >= CUTOFF_SEC:
            continue

        # Annotations
        annotations = []
        for vid, thai, *_ in VOCAB:
            for (a, b) in find_positions(s["thai"], thai):
                annotations.append({"start": a, "end": b, "vocab_id": vid})
                vocab_freq[vid] += 1
        # De-overlap (keep earlier-starting longer matches)
        annotations.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        merged = []
        last_end = -1
        for a in annotations:
            if a["start"] >= last_end:
                merged.append(a)
                last_end = a["end"]
        s["annotations"] = merged

        # Translation + highlight from ENRICHMENT
        idx_str = s["id"].rsplit("_", 1)[1]
        if idx_str in ENRICHMENT:
            e = ENRICHMENT[idx_str]
            s["translation"] = e["trans"]
            s["is_highlight"] = e["highlight"]
        else:
            s.setdefault("translation", "")
            s.setdefault("is_highlight", False)

    # Update freq counts
    for v in vocab_objs:
        v["frequency"] = vocab_freq[v["id"]]
    vocab_objs.sort(key=lambda v: -v["frequency"])

    (DATA / "sentences.json").write_text(json.dumps(sentences, ensure_ascii=False, indent=2))
    (DATA / "vocab.json").write_text(json.dumps(vocab_objs, ensure_ascii=False, indent=2))

    enriched = sum(1 for s in sentences
                   if s["video_id"] == VIDEO_ID and s["start"] < CUTOFF_SEC and s.get("annotations"))
    highlights = sum(1 for s in sentences
                     if s["video_id"] == VIDEO_ID and s["start"] < CUTOFF_SEC and s.get("is_highlight"))
    print(f"  ↳ {len(VOCAB)} vocab entries")
    print(f"  ↳ {enriched} sentences with vocab annotations")
    print(f"  ↳ {highlights} sentences marked as highlights")
    print(f"  ↳ top 5 words by frequency:")
    for v in vocab_objs[:5]:
        print(f"       {v['thai']:25} ({v['romanization']}) — {v['frequency']}×")


if __name__ == "__main__":
    enrich()
    print("✅ Enrichment done")
