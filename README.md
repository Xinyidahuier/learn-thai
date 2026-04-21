# Learn Thai — 商业泰语自学系统

从泰语视频/音频/文字里提取可学习文章，精读 + SRS 复习。

## 访问

本地开发：
```bash
cd /Users/xinyi/学习/Thai/learn-thai
python3 -m http.server 8765
```
访问 http://localhost:8765/

## 添加新文章

三种输入方式，统一走 `add_article.py`：

```bash
# 1. YouTube 链接
python3 scripts/add_article.py --url "https://www.youtube.com/watch?v=XXX"

# 2. 本地音频文件
python3 scripts/add_article.py --audio path/to/file.mp3 --title "泰语播客 EP.1"

# 3. 纯泰文文章
python3 scripts/add_article.py --text path/to/thai.txt --title "泰国商报文章"
```

处理流程：
- YouTube / 音频：Whisper large-v3 转写（泰文 + 英文翻译）→ 句子合并（≤15秒/段）→ 音频切片 → 词汇标注
- 纯文本：段落切分 → 词汇标注

数据会追加到 `data/articles.json` + `data/sentences.json`，刷新浏览器即可。

## 数据结构

```
data/
├── articles.json       # 文章元信息
├── sentences.json      # 所有句子
└── vocab.json          # 词汇库

audio-local/<article_id>/<sentence_idx>.mp3
```

文章对象：
```json
{
  "id": "...",
  "title": "...",
  "type": "youtube" | "audio" | "text",
  "source_url": "...",
  "duration_sec": 2327.6,
  "sentence_count": 210,
  "status": "studying" | "finished",
  "favorite": false,
  "created_at": "2026-04-21T..."
}
```

## 页面

- **首页** `/` — 收藏 / 正在学 / 已学完 分区
- **阅读器** `/reader.html?a=<id>` — 转录 + 词汇弹窗 + 句级音频 + 收藏/学完按钮
- **复习** `/review.html` — SRS 闪卡（SM-2 算法），复习你收藏的词和句
- **词汇库** `/vocab.html` — 所有词汇，按频次排序

## 依赖

```bash
brew install yt-dlp whisper-cpp ffmpeg
# Whisper large-v3 模型：~/models/ggml-large-v3.bin (3GB)
```
