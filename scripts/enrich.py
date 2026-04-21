#!/usr/bin/env python3
"""
Enrich ALL merged sentences for the RAVIPA video with:
- Business vocab bank (curated)
- Word-level annotations (scanning for vocab in each sentence)
- Chinese translations for every sentence
- is_highlight flag for key business paragraphs

Usage: python3 scripts/enrich.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VIDEO_ID = "Nf-KbZ0XHMU"

# ---------------------------------------------------------------------------
# Vocabulary bank
# ---------------------------------------------------------------------------
VOCAB = [
    # Core business terms
    ("v_botrian",      "บทเรียน",         "bòt-rian",              "经验教训 (lesson)",                          "n.",  ["business"]),
    ("v_senthaang",    "เส้นทาง",         "sên-thaang",            "路径、历程 (path, journey)",                 "n.",  ["business"]),
    ("v_təəptoo",      "เติบโต",          "təə̀p-too",             "成长、发展 (to grow)",                       "v.",  ["business"]),
    ("v_saangbraen",   "สร้างแบรนด์",     "sâang braen",           "打造品牌 (build a brand)",                   "v.",  ["business"]),
    ("v_braen",        "แบรนด์",          "braen",                 "品牌 (brand)",                               "n.",  ["business"]),
    ("v_prasopsamret", "ประสบความสำเร็จ", "prà-sòp khwaam-sǎm-rèt","成功 (to succeed)",                          "v.",  ["business"]),
    ("v_ongkɔɔn",      "องค์กร",          "ong-kɔɔn",              "组织、机构 (organization)",                  "n.",  ["business"]),
    ("v_khayaai",      "ขยาย",            "khà-yǎai",              "扩张、扩大 (to expand)",                     "v.",  ["business"]),
    ("v_yɔɔmpɛɛ",      "ยอมแพ้",          "yɔɔm-pɛ́ɛ",             "放弃、认输 (to give up)",                    "v.",  ["general"]),
    ("v_prathet",      "ประเทศ",          "prà-thêet",             "国家 (country)",                             "n.",  ["general"]),
    ("v_jiwənrii",     "จิวเวลรี่",       "jiu-wəl-rîi",           "珠宝 (jewelry) — loanword",                  "n.",  ["business"]),
    ("v_oem",          "OEM",             "oo-ii-em",              "代工生产 (Original Equipment Manufacturing)", "n.",  ["business"]),
    ("v_phalit",       "ผลิต",            "phà-lìt",               "生产、制造 (produce)",                        "v.",  ["business"]),
    ("v_waeluu",       "แวลู",            "wɛɛ-luu",               "价值 (value) — loanword",                    "n.",  ["business"]),
    ("v_ip",           "intellectual property", "in-ter-lék-chuân prɔ́ɔ-pəə-tîi", "知识产权 (IP)",            "n.",  ["business"]),
    ("v_diisai",       "ดีไซน์",          "dii-sai",               "设计 (design) — loanword",                   "n.",  ["business"]),
    ("v_diisainəə",    "ดีไซเนอร์",       "dii-sai-nəə",           "设计师 (designer)",                          "n.",  ["business"]),
    ("v_design",       "design",          "dii-sai",               "设计 (design)",                              "n.",  ["business"]),
    ("v_designer",     "designer",        "dii-sai-nəə",           "设计师 (designer)",                          "n.",  ["business"]),
    ("v_enduser",      "End user",        "en-yuu-sə̂ə",           "终端用户 (end user)",                        "n.",  ["business"]),
    ("v_bukbəək",      "บุกเบิก",         "bùk-bə̀ək",             "开拓、开创 (pioneer)",                       "v.",  ["business"]),
    ("v_kruithaang",   "กรุยทาง",         "krui-thaang",           "开路、铺路 (pave the way)",                  "v.",  ["business"]),
    ("v_global",       "global",          "glôo-bɔɔn",             "全球的 (global) — loanword",                 "adj.",["business"]),
    ("v_saakha",       "สาขา",            "sǎa-khǎa",              "分店、分公司 (branch)",                      "n.",  ["business"]),
    ("v_tangprathet",  "ต่างประเทศ",      "tàang prà-thêet",       "国外、海外 (foreign, abroad)",               "n.",  ["business"]),
    ("v_online",       "ออไลน์",          "ɔɔn-lai",               "线上 (online) — loanword",                   "adj.",["business"]),
    ("v_popup",        "ป๊อปอัป",         "pɔ́p-àp",               "快闪店 (pop-up)",                            "n.",  ["business"]),
    ("v_luukkhaa",     "ลูกค้า",          "lûuk-kháa",             "顾客、客户 (customer)",                      "n.",  ["business"]),
    ("v_patjai",       "ปัจจัย",          "pàt-jai",               "因素 (factor)",                              "n.",  ["general"]),
    ("v_raangwan",     "รางวัล",          "raang-wan",             "奖项 (award)",                               "n.",  ["business"]),
    ("v_tɔɔyɔɔt",      "ต่อยอด",          "tɔ̀ɔ-yɔ̂ɔt",            "延展、扩展 (build upon)",                    "v.",  ["business"]),
    ("v_khwaammaai",   "ความหมาย",        "khwaam-mǎai",           "含义、意义 (meaning)",                       "n.",  ["general"]),
    ("v_khɔɔngkhwan",  "ของขวัญ",         "khɔ̌ɔng-khwǎn",         "礼物 (gift)",                                "n.",  ["general"]),
    ("v_ig",           "ไอจี",            "ai-jii",                "Instagram — loanword",                       "n.",  ["marketing"]),
    ("v_khunnaphaap",  "คุณภาพ",          "khun-na-phâap",         "质量、品质 (quality)",                       "n.",  ["business"]),
    ("v_ookaat",       "โอกาส",           "oo-kàat",               "机会 (opportunity)",                         "n.",  ["business"]),
    ("v_collab",       "Collab",          "khɔɔn-lɛ̂ɛp",           "合作 (collaboration) — loanword",            "n.",  ["business"]),
    ("v_collection",   "Collection",      "khɔɔn-lék-chân",        "系列 (collection) — loanword",               "n.",  ["business"]),
    ("v_disney",       "Disney",          "dít-nîi",               "迪士尼",                                     "n.",  ["business"]),
    # Additional business terms for later content
    ("v_prakuat",      "ประกวด",          "prà-kùat",              "参赛、竞赛 (compete, enter contest)",         "v.",  ["business"]),
    ("v_jutpliian",    "จุดเปลี่ยน",      "jùt-pliàn",             "转折点 (turning point)",                     "n.",  ["business"]),
    ("v_tarlaat",      "ตลาด",            "tà-làat",               "市场 (market)",                              "n.",  ["business"]),
    ("v_yokradap",     "ยกระดับ",         "yók rá-dàp",            "升级、提升 (upgrade, raise level)",          "v.",  ["business"]),
    ("v_patiseet",     "ปฏิเสธ",          "pà-tì-sèet",            "拒绝 (refuse, reject)",                      "v.",  ["business"]),
    ("v_oodəə",        "ออเดอร์",         "ɔ̀ɔ-dəə",               "订单 (order) — loanword",                    "n.",  ["business"]),
    ("v_phuumjai",     "ภูมิใจ",          "phuum-jai",             "自豪、引以为荣 (proud)",                     "v.",  ["general"]),
    ("v_sme",          "SME",             "ɛs em ii",              "中小企业",                                   "n.",  ["business"]),
    ("v_qc",           "QC",              "khiu-sii",              "质量控制 (Quality Control)",                 "n.",  ["business"]),
    ("v_takeoff",      "take-off",        "théek-ɔ́f",              "起飞 (take-off)",                            "n.",  ["business"]),
    ("v_investor",     "อินเวสเตอร์",     "in-wét-təə",            "投资人 (investor)",                          "n.",  ["business"]),
    ("v_longthun",     "ลงทุน",           "long-thun",             "投资 (invest)",                              "v.",  ["business"]),
    ("v_investment",   "เงินเวสเมนต์",    "ngən-wét-mên",          "投资款 (investment)",                        "n.",  ["business"]),
    ("v_approach",     "approach",        "áp-prôot",              "接洽 (approach)",                            "v.",  ["business"]),
    ("v_pricepoint",   "price point",     "phrái-phɔi",            "价格带 (price point)",                       "n.",  ["business"]),
    ("v_sellingpoint", "Selling Point",   "sel-ling pɔi",          "卖点 (selling point)",                       "n.",  ["business"]),
    ("v_positioning",  "Positioning",     "phɔ-sí-chân-ning",      "定位 (positioning)",                         "n.",  ["business"]),
    ("v_localize",     "โลโคลายซ์",       "loo-khoo-lai",          "本地化 (localize)",                          "v.",  ["business"]),
    ("v_exclusivity",  "Exclusivity",     "ik-sà-khluu-sí-wí-tîi", "独家性 (exclusivity)",                       "n.",  ["business"]),
    ("v_exclusive",    "Exclusive",       "ik-sà-khluu-sîp",       "独家 (exclusive)",                           "adj.",["business"]),
    ("v_lifestyle",    "Lifestyle",       "lái-sà-tai",            "生活方式 (lifestyle)",                       "n.",  ["business"]),
    ("v_minimal",      "minimal",         "mí-ní-mân",             "极简 (minimal)",                             "adj.",["business", "design"]),
    ("v_valueadded",   "value added",     "wɛɛ-luu-ét-dìt",        "附加值 (value added)",                       "n.",  ["business"]),
    ("v_brandidentity","brand identity",  "brɛn ai-dɛn-tí-tîi",    "品牌识别 (brand identity)",                 "n.",  ["business"]),
    ("v_vision",       "Vision",          "wí-chân",               "愿景 (vision)",                              "n.",  ["business"]),
    ("v_softpower",    "Soft Power",      "sɔ́f pá-wə̂ə",           "软实力 (soft power)",                        "n.",  ["business"]),
    ("v_creativity",   "creativity",      "khrii-ee-tí-wí-tîi",    "创造力 (creativity)",                        "n.",  ["business"]),
    ("v_passion",      "แปชชั่น",         "phɛɛt-chân",            "热情 (passion)",                             "n.",  ["business"]),
    ("v_standard",     "standard",        "sà-tɛn-dàat",           "标准 (standard)",                            "n.",  ["business"]),
    ("v_believe",      "believe",         "bi-líiv",               "相信 (believe) — loanword",                  "v.",  ["business"]),
    ("v_training",     "เทรนนิง",         "treen-ning",            "培训 (training)",                            "n.",  ["business"]),
    ("v_recruiting",   "ริคูตติง",        "rí-khrûu-tîng",         "招聘 (recruiting)",                          "n.",  ["business"]),
    ("v_regulation",   "Regulation",      "rek-kìu-lee-chân",      "法规 (regulation)",                          "n.",  ["business"]),
    ("v_adapt",        "Adapt",           "á-dǎep",                "适应、改造 (adapt)",                         "v.",  ["business"]),
    ("v_styleguide",   "Style Guide",     "sà-tai-gáai",           "设计规范 (style guide)",                     "n.",  ["business"]),
    ("v_inspiration",  "Inspiration",     "in-sà-pi-ree-chân",     "灵感 (inspiration)",                         "n.",  ["business"]),
    ("v_thinkbeyond",  "think beyond",    "thíng bi-yón",          "超前思考 (think beyond)",                    "v.",  ["business"]),
    ("v_fastmoney",    "fast money",      "fâst mán-ni",           "快钱 (fast money)",                          "n.",  ["business"]),
    ("v_daara",        "ดารา",            "daa-raa",               "明星 (celebrity, star)",                     "n.",  ["general"]),
    ("v_tittam",       "ติดตาม",          "tìt-taam",              "追随、关注 (follow)",                        "v.",  ["general"]),
    ("v_tiisi",        "เทียร์",          "thiàa",                 "层级、梯队 (tier)",                          "n.",  ["business"]),
    ("v_tangchaat",    "ต่างชาติ",        "tàang-châat",           "外国人、外国的 (foreign, foreigner)",        "n.",  ["business"]),
    ("v_multibrand",   "Multi Brand",     "mân-ti brɛn",           "集合店 (multi-brand retail)",                "n.",  ["business"]),
    ("v_buyer",        "buyer",           "bai-yə̂ə",              "买手 (buyer)",                               "n.",  ["business"]),
    ("v_collaboration","คลาบเบอร์เฟรชัน", "khɔn-læp-ə-ree-chân",   "合作 (collaboration)",                       "n.",  ["business"]),
    ("v_challenge",    "challenge",       "chɛɛn-lén",             "挑战 (challenge)",                           "n.",  ["business"]),
    ("v_unique",       "unique",          "yuu-níik",              "独特 (unique)",                              "adj.",["business"]),
    ("v_combine",      "combine",         "khɔm-bai",              "结合 (combine)",                             "v.",  ["general"]),
    ("v_recharge",     "take a break",    "théek-ə-breek",         "休息、充电 (take a break)",                  "v.",  ["general"]),
]

# ---------------------------------------------------------------------------
# Sentence-level enrichment: {idx: (translation, highlight)}
# ---------------------------------------------------------------------------
ENRICHMENT = {
    "0001": ("我们来聊聊这些经验教训，或者说成长之路上的种种。先讲讲必须要付出的代价比较好——走到今天这一步。", True),
    "0002": ("这位（嘉宾）是个特别的人。我理解把品牌做到这个规模并非只有收获——必然有我们要付出的代价。", True),
    "0003": ("很多人可能会说我们多么成功，但 Sa 说：没人知道我们有多累。真的非常累。就像——我们越成长，组织越大，扩张越多，挑战就越难。", True),
    "0004": ("虽然很难，但我们不要向它投降。这是 Sa 每天对自己说的话：「如果容易，所有人都去做了。」然后告诉自己：「旧的钥匙，打不开新家的门。」", True),
    "0005": ("大家好，我是 Khen Nakharin，这里是 The Secret Sauce.", False),
    "0006": ("由 Ravipa 赞助播出。", False),
    "0007": ("大家好，我是 Khen Nakharin,这里是 The Secret Sauce.", False),
    "0008": ("由 Ravipa 赞助。我必须先做个铺垫，让大家能明白——", False),
    "0009": ("泰国一直以珠宝业闻名，但我感觉大部分都是 OEM（代工）——我们为世界各大品牌代工生产。", True),
    "0010": ("但 Ravipa 这个品牌处在价值链最高端的位置。", True),
    "0011": ("哇，不敢轻易尝试啊！", False),
    "0012": ("哇，不敢这么解释吗？意思是——", False),
    "0013": ("思想的价值，对吧？知识产权（IP）——设计的价值。然后是真正拥有品牌、面向 End User（终端用户，即普通消费者）。我很幸运能从最早期就看到 Sa 创业。", True),
    "0014": ("应该是疫情后初期，那时 Moo 系列开始走红。再后来一个阶段，是 Sa 开始与 Disney 这类品牌合作（Joint / Collab）——是泰国最早一批做的人。但今天还有更好的消息。", True),
    "0015": ("作为能把这个故事传达给所有人的人我很高兴——大家能得到宝贵的经验教训：Sa 是开拓者、是铺路人，今天她的品牌是——", True),
    "0016": ("——真正全球化（Global）的珠宝品牌。所以想先问：今天 Ravipa 处在什么阶段了？——好的。从那天起，（Ravipa）是一个线上（online）品牌——", True),
    "0017": ("小小的 pop-up 店，跟姐姐两个人亲自去卖、自己收摊。到今天已经有约 40 家分店了——泰国有，也有海外。目前在 3 个海外国家。", True),
    "0018": ("有澳门、日本，还有香港 2 家。——刚才说海外 3 家主要在哪里？——在澳门，是 Galeries Lafayette（老佛爷百货）。", True),
    "0019": ("哦，是巴黎那家大百货的（澳门分店）！然后——日本店在 Disney Store Japan，就在新宿。再两家是香港 K11 Musea 和 Harbour City。", True),
    "0020": ("都开在真正的全球地标位置。说到「国外」这个词——今天「Global」在你心目中的含义是什么？——我认为全球化就是被更多人喜爱，不只是在泰国有客户。", True),
    "0021": ("不只是泰国人，而是客户遍及海外。今天想聊聊：是怎么走到这个层次的？从我最早看到你的那一天起——简单总结一下走过的路，到今天这个全球化阶段。", True),
    "0022": ("你觉得有哪些因素，让你走到了今天这一步？", True),
    "0023": ("我跟姐姐是从设计珠宝起步的。我们是珠宝设计领域获奖很多的品牌——从一个小小的设计师（designer）品牌开始，赢了许多奖，把奖金不断延展投入业务。", True),
    "0024": ("Ravipa 的珠宝必须是真能戴的、每天都能戴，并且要有意义。如果只是好看的珠宝实在太多了——我们必须做出能真正每天佩戴的珠宝，里面蕴含意义、积极、幸运的元素，让顾客觉得想买来送给自己。", True),
    "0025": ("是送给自己庆祝某事的 gift，也是送给心爱之人的 gift。但「有意义（meaningful）」这个词范围太广了……其中一个真正击中人心的，就是「幸运（Lucky）」这个词。", True),
    "0026": ("那么，我能请你举几个例子吗？我会从最早期开始介绍。我的团队已经准备好了，举三个时期为例。", False),
    "0027": ("对吧，这样我们就能看到——好的。", False),
    "0028": ("「I believe it.」听众朋友们谢谢大家——你们会看到第一个时期。对自己来说，比如那些在 IG 上做小生意的年轻人，让他们看到这里有 know-how。因为 Ravipa 应该是 IG 最早一批的开拓者——IG 刚兴起就开始做了。", True),
    "0029": ("然后在 K Village 那种地方卖，对吧？", False),
    "0030": ("我记得！记得出 booth 的样子，我有照片，待会儿放图——因为这真的就是起点，第一个 Collection，就是这一个 Collection。这里面有什么关于今天全球化的 know-how？或者关于设计演进（evolution）的 know-how？", True),

    # Era 1: Infinity origin story
    "0031": ("好，那从 Infinity（无限符号）讲起。从 Day 1 起，Sa 就说：我们想要……当时我还在大学三年级，跟姐姐说想要一枚 Infinity 戒指。她问：为什么想要？我说——", False),
    "0032": ("我想要一枚定情戒指。但普通的戒指太大众了——我想要有意义的。而 Infinity 的含义也很好。——对。这就是起点。Sa 真的很幸运——", False),
    "0033": ("Ravipa 的 First Step（第一步）是一个 Success（成功）的 First Step。", True),
    "0034": ("——哦，就是这一款 Infinity！——就是它。因为当时是在情人节前推出的。", False),
    "0035": ("——哦……哦……那个时机真的非常好。事实上后来大家看到的都是这样 boom、boom、boom 扩散出去的。", False),
    "0036": ("Infinity 不是我们发明的——它存在很久了。但是我们把它设计成 minimal（极简）风格。", True),
    "0037": ("——而且是真正能日常佩戴的。", False),
    "0038": ("——就是这些 Sa 用心雕琢的小细节（detail）。", False),
    "0039": ("比如这里——Ked 你看这边——没有任何挂钩、任何容易勾到衣服的东西。因为 Sa 希望它能真正「Everyday（每天戴）」。是与众不同的 Infinity——姐姐设计了一个从没人做过的曲线形状。", True),
    "0040": ("也就是说，姐姐——", False),
    "0041": ("——对对，她作为 Designer，设计很强。然后从 Sa 本人那里得到了任务：想要有意义的东西。", False),
    "0042": ("一开始，什么让顾客愿意掏钱买？那时的珠宝价位也不便宜。顾客说：这个设计真的独一无二。他们说：「我早就喜欢爱情的承诺、Infinity 符号很久了，但从没见过对的设计。」", True),
    "0043": ("关键词就是「设计」——在那个还没有「Branding（品牌营销）」这个概念的年代。第一个时期，就像「出道成名」。这就像今天 IG 上做这类生意的年轻人——不管是珠宝、时装还是生活方式——设计必须与众不同，必须先击中人。", True),
    "0044": ("——在那一天（打响名号）之后再延展（扩大业务）。来到第二个时期吧——我们看看第二个时期。这是什么时期？", False),
    "0045": ("是一个时期吗？好的。这个时期可以称为转折点（Design Award）——能参赛设计大奖（Demark Award），灵感来自于「想要幸运，但不张扬」。", True),
    "0046": ("这个跟前面有点不同：这个是「设计（Design）先行」；这个「Meaningful（有意义）」开始变得清晰；并且是 Coverage（市场覆盖）——不只是泰国人，而是整个亚洲（Asia）。", True),
    "0047": ("亚洲一些市场已经认识我们，所以不用从零 Educate（教育市场）。这让这个系列可以说是 Ravipa 真正的「take-off（起飞）」节点——对吗？", True),
    "0048": ("从 baby step（小步走），突然要跳上喷气机（jet）。自己却还没准备好——还不会开喷气机。我想用这个比喻——当时为什么会觉得自己不会开喷气机？", True),
    "0049": ("那时候 Global Star 开始有人穿戴——Lizzo 穿、Jackson 穿，一个接一个，最近（2NE1的）CL 也穿。突然之间就得上喷气机了——光靠开车不够用了。", True),
    "0050": ("因为机会不断涌进来。喷气机的比喻是说——订单多到接不过来。收到了来自多个国家的反响。团队跟 Sa 说：姐，我们不只是泰国客户了。", True),
    "0051": ("但外国人涌进来，而我们从来没有讲英语的销售员——不得不去找会英语、会中文的员工，或会三门语言的人。那时候，这架「喷气机」怎么才开得起来？靠什么抓住机会成功？", True),
    "0052": ("因为必须承认，很多 SME——", False),
    "0053": ("比如做食品的，有机会打进 7-Eleven，但产能跟不上——因为产能不够，没法抓住机会，质量反而下滑——最后反噬回来。", True),
    "0054": ("——但 Sa 坚信：「Promise made, Promise kept（承诺了就要做到）」。承诺给客户好的东西——没做好就不要送。", True),
    "0055": ("——是吗？哦哦哦——绝对不能糊弄、欺骗客户。我们有内部（in house）QC 团队——不合格就重做，不合格就等。质量不达标绝不出货。", True),
    "0056": ("全部都等——没做完就等，绝不匆忙出货。当时工厂曾经 offer 更快的做法，但细节会受影响——不行，不做。那时候其实蛮有骨气的——因为拒绝了一大笔钱。", True),
    "0057": ("——因为订单（order）来的时候——我要说的就是：这就是 SME 的致命点。", True),
    "0058": ("——即——SME 一接到大订单，或者想升级（自我提升）的时候，会愿意降低自己的 Quality 来换大笔钱，对吧？但当时为什么 Sa 敢拒绝钱，坚守 Quality？从某种角度来看似乎——", True),
    "0059": ("——不聪明。你回答说：这样做就抓不住机会了。为什么这么想？结果怎么样？Sa 说：我非常以这个品牌为傲（ภูมิใจ），它就像我的孩子。大家都知道我是创始人，我不想毁了它的名声。", True),
    "0060": ("Sa 觉得——我们不想拿这笔钱，然后失去一切。Sa 跟团队说：在我创立这个品牌之前，花了很长很长时间，经历了很多。", True),
    "0061": ("如果为了这笔钱孤注一掷——", False),
    "0062": ("——可能会失去全部。Sa 不想让一直追随（ติดตาม）我们的客户失望。", True),
    "0063": ("——我觉得想一想，再想一想——老师你不是第一个遇到这种困境的人。这没有对错，在于你怎么选。如果选短期的路，快速成长、赚大钱，也许挺好，说不定——", True),
    "0064": ("但在反面，代价可能会发生——如果你的品牌受损，或者马上就有人赶超你。你可以选另一条路——", True),
    "0065": ("就是选那条让品牌先变强的路。", True),
    "0066": ("对吧？在那段时间，当我们选了这条路，后来有没有额外的转折点让我们再次跃升？可能是时机，加上一点运气。就是：每一个进入 Sa 生命的机会——", True),
    "0067": ("不管是无数的海外百货，还是世界级的明星（Sa 肯定请不起他们）——这些机会都源于我们对 Quality 的不屈服。销售员或每天出货的同事——", True),
    "0068": ("——都不知道这一件会落到谁手里，因为所有人都可能是顾客。他们戴了之后印象深刻、赞赏，后来主动联系，成为 business partner（商业伙伴）。", True),

    # Era 3: Disney collaboration
    "0069": ("这个时期是更加全球化的时期，跟海外品牌合作（collab）。啊，这里一看就明白——米老鼠 Mickey Mouse。", True),
    "0070": ("回忆一下——当时那个机会是怎么来的？", False),
    "0071": ("当时是他们先来找我们的。Sa 本来就是 Big Disney fan——很想做。当时完全没看 business term（商业条款），Sa 跟姐姐说：这是梦想中的品牌，是我爱的、执着于 Disney 的品牌。", True),
    "0072": ("Sa 从小就被爸爸扛在肩上看烟火——现在已经扛不动了。很幸运那一次的决定和合作，让我们不只在泰国成长——还开到韩国、日本。", True),
    "0073": ("是他们历史上第一个泰国品牌。我想很多人跟我有同样的问题——怎么样才能搭上 Disney？Sa 说：有一个超级难的点——不只是让他们对我们感兴趣，而是——", True),
    "0074": ("——不只是「买图案」这种只要有钱就能买的事——而是怎么让自己变得「不同」，在跟 Disney 一起摆在全球货架上的时候脱颖而出。这是最难的——如果要说做 Disney 最难的部分，就是这个。", True),
    "0075": ("我们必须 think beyond（超前思考），让一切真正 make it different（做出差异）。他们的 Style Guide 给每个合作方都一样，Manual Book 也都一样——但如何把「基础的（Basic）」内容 Adapt 出差异，那才是最难的。", True),
    "0076": ("——这是最难的一点，对——就是让他们觉得我们做得超出预期。", True),
    "0077": ("——对，Adapt Design 怎么做到「不雷同」。因为全球做 Disney 联名（Brand JV）的品牌太多了。当时 Sa 把方案送去 Cool Branding 评审——他们把资料送到美国——问这个品牌你们接不接？", True),
    "0078": ("因为 GVW（Global Vertical Window）全球只接几个品牌。当时里面全是大牌——所有大家耳熟能详的品牌都在做。那为什么 Ravipa 能入选？为什么要让一个泰国的品牌进来？", True),
    "0079": ("因为我们的国家根本不在他们关注的第一梯队（Tier）里。对——但最终得到的答复是：他们见过很多，但（我们）真的「不一样」。", True),
    "0080": ("——回到最初，就是「差异」——就是我们刚才聊的。能举个例子说说让 Disney 眼前一亮的「差异」是什么吗？", True),
    "0081": ("——以 product（产品）为例也可以？", False),
    "0082": ("——可以。就拿这款 Mickey，因为是第一个 collection。Disney Style Guide 里的这款 Mickey，你看他好像在 paint（画画）什么东西。但 Sa 说：以它的这个姿态，我想改成他在挂一个 Infinity——诶，我刚注意到！对，就是这样。", True),
    "0083": ("Infinity 是 Ravipa 的起点，而 Mickey 是人人都认识的符号——Disney 和 Mickey Mouse 本来就是一对。所以这是首个 kickoff。细节特别多——是两个品牌融合进一个产品。", True),
    "0084": ("哇，换作是我也会爱上。真可爱。——谢谢！——一开始粗看，以为只是普通的 Disney、Mickey，但仔细看——他好像在举着什么，而 Infinity 就在那里——所以「Lucky（幸运）」还在——", True),
    "0085": ("还有 Lucky——Brand Positioning（品牌定位）没变。Infinity 里依然藏着「幸运」的寓意。这款角色同样藏着 Lucky。这个角色是在日本首发的——", True),
    "0086": ("是 Zootopia 和 Stitch。啊，这是非常重要的阶段。那今天呢？今天已经不只是合作了，而是在那边开店——", True),
    "0087": ("这一步的差异是什么？难在哪里？跟我们（泰国）和其他国家——包括香港、日本——不一样。工作方式、很多东西都不一样。", True),
    "0088": ("对。比如日本人特别喜欢面对面（face to face），非常重视见面——不接受 online meeting，一定要见面。工作时他们态度非常严谨，standard（标准）很高。", True),
    "0089": ("但 Sa 认为这很好——反过来 uplift 了我们品牌的内部（internal）——让我们（团队）升级。跟团队说：我们是在跟这种级别的全球品牌合作——那我们自己也得 uplift 到 global standards（全球标准）。", True),
    "0090": ("Sa 觉得对团队最大的 challenge 是：不只 Sa 本人要能 adapt，整个团队都要能 adapt。面对各种各样的人，因为 Sa 没办法亲临每一个工作场景。", True),
    "0091": ("这说明难点和早期不一样了——不再只是产品、只是设计、或只是服务的问题。而是团队内部的专业性（professional）——如何 upgrade 团队里的人——", True),
    "0092": ("——让他们能够在新系统下工作。", True),
    "0093": ("——对，那团队内部怎么培训？Sa 觉得最挑战的可能是培训海外的销售员。因为这是跨国了、沟通方式都不一样。但我们要建立同样的 believe（信念）、同样的 value（价值观），跟泰国的同事保持一致。", True),
    "0094": ("Sa 很开心——客户去到香港的店说：嘿，感觉像是把泰国的销售员搬到了香港一样（感受一致）。", True),
    "0095": ("——这就是——对，是 Local 的人、是香港人——我们怎么让他们说出的话跟泰国员工一样？怎么让他们拥有相同的 mindset？靠 training（培训）。但更重要的是上一个步骤——Recruiting（招聘）。", True),
    "0096": ("就是找那些本身就有 believe（信念）的人——他们本来就相信：传递幸运的能量是好事。说「祝你好运」时是发自内心的。就像 Sa 用心、designer 用心，办公室里每个人都用心——", True),

    # Opening offline stores
    "0097": ("我想回头问一下——开那些「海外旗舰点」的时候，最重要的事是什么？（作为真正开店）因为之前只是 collab 或——", False),
    "0098": ("——对，或是 pop-up 之类的，我不确定理解对不对——", False),
    "0099": ("——对，就是过去那种参展。", False),
    "0100": ("如果是参展，我们参展过——3 天、5 天。但这个是「永久」的——如果他们不改规则。", True),
    "0101": ("——所以是 Investment（投资）了？——是的，我们得投资、建店。因为我跟很多泰国品牌聊过——我想——", True),
    "0102": ("——对，做比较，让大家看清楚——这可能是一堂课。去到那个阶段的泰国品牌是有的，但大多数是 Multi Brand（集合店）的模式。", True),
    "0103": ("——我也经历过那个 Stage（阶段）。", False),
    "0104": ("——Multi Brand 阶段，也算很厉害了。或者参展后被大 buyer（买手）采购。但真正「有自己的店、用自己名字」的，可能不多——可能有一些。我可能说不完整，但——", True),
    "0105": ("问题是——为什么做这个决定？有合伙人（ผู้ร่วมทุน）吗？第二——自己开店到底多难？——一句话：自己扛（ลุยเอง）。自己去香港开公司。", True),
    "0106": ("用我们自己的团队把一切搭起来。为什么觉得是时候了？——有人邀请？看到市场？还是——那家百货（Galeries Lafayette）来 approach 我们，而且是我们非常喜欢的百货。", True),
    "0107": ("平时去旅游我们就爱去那家逛。我们觉得他们的品牌选品好得不得了——我们想成为「邻居品牌（Brand Peer）」——泰语里叫「邻居」，就是旁边的品牌，是我们仰望的（look up to）品牌。", True),
    "0108": ("那是我们想跻身的地方——Lifestyle 层面，一个客户 From head to toe（从头到脚）都能穿戴——而那里就是——", True),
    "0109": ("——「From head to toe」，她住在那里。我们周围有什么品牌？有 Lululemon、Issey Miyake——服饰里有 Sandro Marcez，价位在 10,000 铢以上，是 Designer Brand 那一档。", True),
    "0110": ("——对，不算 Ultra Luxury 顶级奢华，但是 Affordable Luxury（轻奢）。", True),
    "0111": ("——正好就是我们（的定位）！为什么他们（百货）找我们？回到最初——Sa 也问过他们。他们说：这个品牌真的「不一样」——他们考察过很多，但还是选 Ravipa。他们说：你知道吗，你们的设计独一无二。", True),
    "0112": ("他们说：如果是 Affordable Luxury 生活风格——Sa 认为这是一个正在走红的趋势——Lifestyle Brand，顾客因为生活方式而买单，而不是单单因为一件产品。", True),
    "0113": ("——对，他们说：是「能日常穿着（Affordable）」的生活，而且还有意义。没有品牌 Positioning 在这个位置。这是我们 Day 1 就相信的——有点运气（幸运），让我们依然坚守在那个点。", True),
    "0114": ("对。到今天他们也觉得我们「不同」，有清晰的 Selling Point——关于 Lucky，而且这是他们生活方式的一部分。他们说：新一代的 Lifestyle 就是 Ravipa。Sa 那天听到眼泪都要出来了。", True),
    "0115": ("作为租户、作为 Real Estate（地产）的所有方，他们当然会重新审视自己的客户——客户喜欢什么？他们一定做过 Survey（调研）。", True),
    "0116": ("当他们想吸引「有品位（trendy）」的新客群，我们品牌正好在那个位置——因为我们不同。但要真正去开店，到底有多难？", True),
    "0117": ("这件事说起来很简单——但 Suppliers、一切、都要从新开始——全部要重新学——所有 Regulation（法规）都要重新学。From Zero（从零开始）——唯一不 from zero 的是 Product。", True),
    "0118": ("最重要的 lesson 我想分享给大家：在泰国的 Hero Product（爆款产品），未必是香港的 Hero。另外，Sa 想说——每个地方都喜欢 Exclusivity（独家性）。", True),
    "0119": ("客户经常来泰国——为什么一定要在香港买？这是好问题。要感谢客户——Sa 喜欢跟客户聊。回到第一个答案——就是客户。他们说：这里有什么 Exclusive Product？而我们有。", True),
    "0120": ("他们说：哎，所以我才会在这里买——即使 Exclusive 款卖得很贵——他们不介意，他们就想要那种「特别」，能去炫耀：这个是我在这家店买的。", True),
    "0121": ("——哦，明白了。除了理解行为（behavior），还要——对，理解可能不同的文化——必须 Localize。而这里的「Localize」指的是有什么「特别」的东西，让他们觉得「我必须去香港那家买」。", True),
    "0122": ("或「我必须去日本那家买」——比如日本怎么样？同样也是他们来邀请的——我不想剧透——哦，（笑）还以为都破了（秘密）呢——好，说日本——", False),
    "0123": ("日本那边感兴趣，偷偷去看——但说起来客户、partner 都是以「客户」身份出现。我们不知道哪一件产品会到他们手里——因为他们「伪装成客户」悄悄来考察。", True),
    "0124": ("——对，他们考察得非常仔细——因为他们不想先看我们 present 的资料——想知道作为一个 customer（顾客）的真实感受如何。很严苛。最后他们喜欢我们的产品。", True),
    "0125": ("他们说：他们跟日本品牌做过很多 collaboration。我们去日本会看到——Disney 在他们那里几乎「统治」市场。那为什么还要 Ravipa？他们说：不管怎样，（我们）就是「不一样」。", True),
    "0126": ("做一个 collection 要 6 个月——是不是太长了？不做快时尚（Fast Fashion）——难道不是该赶紧赚钱？——我们坚守原本的原则。今天的外国伙伴——不管是香港还是日本——非常 appreciate 这一点。", True),
    "0127": ("——对，我们的细腻、我们的用心。我换个角度问——这可能涉及到设计师层面——外国人喜欢什么？", False),
    "0128": ("——亚洲、或你（Sa）接触过的全球客户，他们的品味是什么？也许对很多朋友有启发。——Sa 认为是「minimal（极简）」。因为 Ravipa 不做那种张扬的珠宝。", True),
    "0129": ("他们觉得：不张扬，但舒心、还带幸运——幸运就像 value added（附加值）。他们第一眼扫过去，感觉就是 minimal（极简）、真能戴、值。", True),
    "0130": ("——我手腕上这一款——Bucha 刚才给我的——举个例子——这是什么？跟别的品牌有什么不同？Sa 说：因为是能真正日常佩戴的珠宝，而且里面藏着 Lucky（幸运）。", True),
    "0131": ("——不说不知道，这就是重点——「不能明说」。Sa 希望是——这样的幸运——像是在心中对自己的一个小提醒：今天会是美好的一天。", True),
    "0132": ("——这里的「Lucky」具体是什么？", False),
    "0133": ("——下面这一小条的小符号——非常小——Sa 的灵感来自湿婆（Shiva）——也就是湿婆的第三只眼，能「驱除厄运」。这是我们放进 Design 里的 Storytelling——做到最 Minimal。", True),
    "0134": ("——这个图腾是不是要经过真正的开光之类？——是真的吗？我们是有做仪式的。有的师傅会做。但从设计（design）开始，就把祝福、能量放入每一件。", True),
    "0135": ("今天不想让人觉得——穿这件必须配那种衣服。我们的款式——不用想，怎么搭都行、适合任何 look（造型）——这才能真正应对各国的场合。", True),
    "0136": ("——可以说这是「国际通用语言」吗？——对，在 Sa 的观点里，「国际通用」意味着真能用，我用 minimal 这个词——就是适用于任何场合。", True),
    "0137": ("——但如果把泰国 element 加进去呢？这元素可多了——对吧？", False),
    "0138": ("比如那些尖顶装饰（ชฎา）、或三角形、各种传统图腾——我这样发问，是因为我觉得 Sa 是新一代少数真正——", True),
    "0139": ("——把泰式设计元素（的精髓）融入世界级舞台的人之一。——谢谢！换个角度问——你有被人问过吗：这是「泰式」的吗？", True),
    "0140": ("——有吗？——有。那要不要强调「卖泰式」？当要进入外国市场时，人们常说「要强调本土」——其实真要说的话，我们第一款 Original——手腕编绳（ลายถักเชือก）就是。", True),
    "0141": ("这款编绳系列，灵感来自小时候编辫子——女生在学校里编头发——它跟我的发辫是同一种纹路。是一种手工艺（craftsmanship）——这条手绳不是单根绳，是要「编」出来的。", True),
    "0142": ("而编的时候——相信我——非常难。每一根的张力都要一致——就像小时候妈妈给我们编辫子，要一点一点扯紧。这算「泰式」吗？在 Sa 看来，「手工艺（handcraft）」就是泰式——因为泰国是——", True),
    "0143": ("——因为泰国是一个非常注重细节的国家。但我们跟其他国家最大的不同，就是细腻度。", True),
    "0144": ("——细腻，但不一定要带传统图腾——对。但要有一些「曲折弯绕」——不用到那个程度。Ravipa 是「细腻」与「极简（minimal）」的结合——而且真能每天戴。", True),
    "0145": ("——对，那我们的细腻跟日本的细腻有区别吗？", False),
    "0146": ("——嗬，不同！", False),
    "0147": ("——哦，是吗？", False),
    "0148": ("——对，日本有他们的 license、他们的 material、他们的 uniqueness。比如泰式线纹（Line Print）跟和服的线纹就非常不同——线条的「质感」也大大不同。", True),
    "0149": ("对，Sa 认为我们必须把自己的 Uniqueness（独特性）拿出来用。我特别喜欢一点：今天大家都在谈 Soft Power——但在设计层面真正的 Soft Power 就是「拿出我们的独特性，调整后变成世界的语言」。", True),
    "0150": ("现在正准备要扩张了。", True),
    "0151": ("——哦，去哪里？——偷偷告诉你，因为我们刚从那里飞回来——准备在香港再开一家店——第二家店。啊，不敢说——现在已经有两家了，敬请期待。", True),
    "0152": ("——太棒了！——对，而且今年我们的计划是——", False),
    "0153": ("——现在也在准备扩张，偷偷告诉你（第一次透露）——刚飞回来，准备在香港开第二家店。", True),
    "0154": ("——是第二家店。", False),
    "0155": ("——不敢说，现在已经有两家了，请大家追踪。", False),
    "0156": ("——太棒了。", False),
    "0157": ("——今年计划是：如果有机会、我们也准备好了，还想继续扩张。其实 Sa 很幸运——有很多百货找我们。但这是一个 lesson learned（经验教训）——回到前面的话题：Sa 不想「贪」。", True),
    "0158": ("——哦——是。因为海外投资比泰国要大得多。从 Day 1 到今天，Sa 一直没借过钱——都用自有资金投资。所以（扩张速度）可能没那么——", True),
    "0159": ("——猛扩、猛扩——对吧？——对，做不到（那样）。", False),
    "0160": ("——对，那你想那样吗？——我觉得我还——其实有 investor（投资人）来找过，肯定的。但我心里还是觉得：我想让这个「孩子」按我们现在养它的方式长大。", True),
    "0161": ("我觉得这个品牌还有潜力（Potential）——想亲自把它推到我手里能到达的最高点。——嗯，所以不是以「钱」为目标？——完全不是。我们想做的是——去到海外能看到自己的品牌。", True),
    "0162": ("旅行时看到自家的店，就像把「孩子」送到国外上学一样幸福——这是另一种对成功的定义。因为 Sa 仍然相信创造力（creativity）——", True),
    "0163": ("——当钱介入太多，creativity 就不会发生。这是 Sa 所 value（重视）的。我不知道这是不是对的、或者是不是每个人都该照搬——但我认为我们是「以设计为本、以激情（passion）为本」。", True),
    "0164": ("如果只想钱，会变成只走容易的路、去赚「快钱（fast money）」。而 brand identity（品牌识别）、我们相信的很多东西，有时候不是 quick money——不会明天就变钱。", True),
    "0165": ("这扇门 Sa 关了很多很多次。——有没有哪次决策让你觉得做错了？有吗？", False),
    "0166": ("——想感谢「每一次」都行，正反两面都感谢。回顾走过的 Journey——第一阶段做 Infinity 那一对（戒指），也许因为当时还在读书，所以每一步都非常 baby step。", True),
    "0167": ("Sa 自己觉得——10 年……其实 12 年了。跟现在比起来算很慢——现在一下子就百万千万了。但当时 Sa 很怕——", True),
    "0168": ("小时候 Sa 非常怕：怕失败、怕被迫收摊、怕最后要去上班。什么都怕。但「怕得太多」让人不敢迈步——所以得感谢那场危机（ที่ทำให้ต้องขึ้นเครื่องบินเจ็ท）——", True),
    "0169": ("才逼自己勇敢上去。而在那之前，我们都——", False),
    "0170": ("——对，非常保守——对。那个机会到来才让今天的这些发生。对——这可能是一堂 lesson learned：不用等到你「准备好」才行动——因为没有所谓「准备好」。我们 baby step 太久了。", True),
    "0171": ("——浪费了很多时间。直到最近几年，这 5 年——才敢。哦——但也未必真的「准备好」才能到那个点。其实没人知道——但这是一个经验教训。", True),
    "0172": ("最后来聊聊「经验」和「成长之路上的代价」吧。", False),
    "0173": ("——走到今天——对。这就是，作为一个人，我理解：把品牌做到这个规模，必然有所牺牲——走这条路、或今天这个自己，都有什么变化？", True),
    "0174": ("嗯……Sa 认为是「责任感」。很多人会说：我们成功了——但 Sa 说：没人知道我们多累。真的很累——我们越成长，组织越大——", True),
    "0175": ("——扩张越多，挑战越难。每天醒来都有 challenge，有很多要突破的东西——是一场永无止境的学习。对——但我们不向它投降。", True),
    "0176": ("这是 Sa 一直用来安慰自己的话：「如果容易，所有人都做了」。还告诉自己：「旧的钥匙绝对打不开新家的门」。哦，很有深意——所以我的任务就是去找新钥匙——", True),
    "0177": ("——去开新家的门。", True),
    "0178": ("——哪怕我看不到有谁拿着那把钥匙——我也得自己去造一把。而且——我们是市场的 leader——这就是我们必须找到钥匙的原因。", True),
    "0179": ("——必须不断开拓、尝试新事物。从心理层面问一下——作为一个承受压力、必须不断找钥匙的 leader，独自一人在安静房间里时——", True),
    "0180": ("你怎么跟自己对话？怎么安慰自己？或怎么给自己注入我们所说的「幸运能量」？是跟姐姐聊？还是跟朋友聊？", False),
    "0181": ("或有什么方法「治愈」自己？Sa 认为这些——小时候（现在 33 岁）——二十多岁时不懂「身体有极限」这件事。", True),
    "0182": ("Sa 是个 Workaholic——但没关系，工作狂就工作一下，等我们恢复就继续奋斗。通宵做事都做得到——因为那时身体扛得住。但现在明白：身体已经不行了。", True),
    "0183": ("——对，有一件事我明白了：「take a break（休息）」——以前 Sa 觉得是浪费时间。我以前一周真的工作 7 天——没夸张。直到 30 岁（Sa 进入 30 岁）才改变——女性过了 30——", True),
    "0184": ("——其实不分男女，所有人都一样。有一件事我学到——「努力工作、不停歇」——我以前觉得休息对不起自己，好像不努力就没人会努力一样。", True),
    "0185": ("——但反过来，「take a break」其实是「recharge（充电）」，为了走得比原来更远。我觉得今天是一堂很好的课。——也从泰国整体来看——今天泰国——", True),
    "0186": ("——如果要摆脱（中等收入）陷阱、跨越高墙——只有一条路——必须注入「Value（价值）」、做更高端的东西、注入 IP（Intellectual Property）、注入 Social Property——", True),
    "0187": ("——注入 Innovation（创新）、注入 Tech——什么都行，每个行业方式不一样。但 Sa 的做法是：Design（设计）、Quality（质量）、Global Language（国际通用语言）——用这些来 uplift（升级）价值。", True),
    "0188": ("如果给想「打造品牌」的人一句建议——", False),
    "0189": ("——不说理论性的东西——因为没人比 Sa 更能给出真实的路径。", False),
    "0190": ("——明白我的意思吗？因为我们（主持人）自己也在做，知道——「要是当时有那个节点，我可能能走更远」、「要是有那个节点，我可能会有同行一起看」之类。不用讲政府层面——", False),
    "0191": ("——仅从经营者个人角度——想把泰国品牌做成——", True),
    "0192": ("——像韩国那样一片一片、百花齐放——那把「钥匙」是什么？从你自己的经验说——对。我认为泰国品牌其实很多——", True),
    "0193": ("——Sa 成长的年代，有很多设计师朋友、前辈都非常厉害，Sa 很尊敬他们，作品也非常出色。", True),
    "0194": ("但今天我看到很多这些品牌已经停掉了。原因是他们的「后劲」不够——设计师本来资金就没那么充裕，又靠 passion 在做。Sa 为很多品牌可惜——尤其疫情期间——", True),
    "0195": ("——正是「考验后劲」的时候，他们只能停下一切，转去做别的 business。我看到很多前辈都这样，非常可惜——泰国人的才华和设计能力不输给任何国家。", True),
    "0196": ("——但他们缺少「展示的舞台」。Sa 很幸运——Sa 参加过很多展会、时装秀、Fashion Week——去过很多国家——靠自己的力量。", True),
    "0197": ("——而且非常贵。我坦白：每次参展都没赚钱过（เก肙 gain）。但我告诉自己：我赚到的是「学习」——拓宽了自己的视野。", True),
    "0198": ("——是我看到、是 Sa 能跟外国客户直接交流——", False),
    "0199": ("——真的？——对，这是「学习的学费」。但几个人愿意付这样的学费？因为它不会直接赚钱——是纯粹的 minus（亏损）。Sa 认为那些人缺乏展示的舞台。", True),
    "0200": ("Sa 觉得必须有舞台来支持、带泰国人走出去。在外国人眼里——以前我以为「Made in Thailand」外国人未必喜欢——有「Made in Japan」就够了。", True),
    "0201": ("但反过来，这对我也是新的一堂课——最近一次洽谈，他们直接说：希望大家知道 Ravipa 就是泰国品牌。哇——耐心地、坚定地（ยึดหลัก）——今天 Sa 坚守原则——哪天——可能会慢一点——", True),
    "0202": ("——但终有人会看到我们设计的 value。想告诉那些放弃的人：回来继续战斗。还有那些承受「外部 supplier、外部（成本）」压力的创业者们——", True),
    "0203": ("——Sa 想说：每个人都在 suffer（挣扎）。但我想说——隧道的尽头会有光，我们必须去找到它。Sa 当时也是「八方漆黑」。但当我们感到——", True),
    "0204": ("——这个 Collection 就是「最后一搏」了——试试看——当我们「All in」的时候，Sa 觉得那是真正的「奇迹之力」——我们非常周密地思考，然后——", True),
    "0205": ("有好的 Vision，所有人朝一个方向冲——公司里每个人都朝同一个 goal 前进。Sa 认为这是我们能挺过危机的关键。每次发生危机——", True),
    "0206": ("——不管是政治新闻、世界经济还是什么——Sa 都告诉团队：我们曾经经历过最难的时刻，那时几乎要倒闭。", True),
    "0207": ("——疫情之类的——对，都熬过来了。那时 Sa 只有 10 几口人——今天有 200 人、有更大的军团。所以大家不用怕，我们一样能熬过。对——这就是我想说的——", True),
    "0208": ("——最后就是——「不要放弃（อย่ายอมแพ้）」，简短一句。但从（你的）经验和今天的成就来看，真的非常感谢你。", True),
    "0209": ("——也祝你鼓起勇气。今天谢谢你。——谢谢大家。", False),
    "0210": ("请继续关注下一集。", False),
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

    for s in sentences:
        if s["video_id"] != VIDEO_ID:
            continue

        annotations = []
        for vid, thai, *_ in VOCAB:
            for (a, b) in find_positions(s["thai"], thai):
                annotations.append({"start": a, "end": b, "vocab_id": vid})
                vocab_freq[vid] += 1
        annotations.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        merged = []
        last_end = -1
        for a in annotations:
            if a["start"] >= last_end:
                merged.append(a)
                last_end = a["end"]
        s["annotations"] = merged

        idx_str = s["id"].rsplit("_", 1)[1]
        if idx_str in ENRICHMENT:
            trans, is_hl = ENRICHMENT[idx_str]
            s["translation"] = trans
            s["is_highlight"] = is_hl
        else:
            s.setdefault("translation", "")
            s.setdefault("is_highlight", False)

    for v in vocab_objs:
        v["frequency"] = vocab_freq[v["id"]]
    vocab_objs.sort(key=lambda v: -v["frequency"])

    (DATA / "sentences.json").write_text(json.dumps(sentences, ensure_ascii=False, indent=2))
    (DATA / "vocab.json").write_text(json.dumps(vocab_objs, ensure_ascii=False, indent=2))

    total = sum(1 for s in sentences if s["video_id"] == VIDEO_ID)
    translated = sum(1 for s in sentences if s["video_id"] == VIDEO_ID and s.get("translation"))
    annotated = sum(1 for s in sentences if s["video_id"] == VIDEO_ID and s.get("annotations"))
    highlights = sum(1 for s in sentences if s["video_id"] == VIDEO_ID and s.get("is_highlight"))
    print(f"  ↳ {len(VOCAB)} vocab entries")
    print(f"  ↳ {translated}/{total} sentences with translations")
    print(f"  ↳ {annotated} sentences with vocab annotations")
    print(f"  ↳ {highlights} sentences marked as highlights")
    print(f"  ↳ top 10 words by frequency:")
    for v in vocab_objs[:10]:
        print(f"       {v['thai']:25} ({v['romanization']}) — {v['frequency']}×")


if __name__ == "__main__":
    enrich()
    print("✅ Full enrichment done")
