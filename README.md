# Media Skills Automation Project

This project automates content creation and publishing for social media platforms, specifically targeting **WeChat Official Accounts** and **Xiaohongshu (Little Red Book)**. It integrates content crawling, AI-powered generation (text & images), and automated publishing capabilities.

## 🚀 Features

### 1. NewRank Crawler (`newrank_skill`)
- Crawls "Hot Subjects" from NewRank (新榜).
- Supports incremental crawling with local deduplication (SQLite).
- Outputs data to JSON for downstream processing.

### 2. WeChat Official Account Automation (`wechat_skill`)
- Generates articles based on input topics (e.g., from NewRank).
- Uses **DashScope (Qwen)** for article writing and **Qwen-VL/Wanx** for cover image generation.
- Automatically syncs drafts to WeChat Official Account Draft Box.
- Prevents duplicate publishing via local history tracking.

### 3. Xiaohongshu Automation (`xiaohongshu_skill`)
- Generates lifestyle notes (text + emoji + tags) suitable for Xiaohongshu.
- Generates cover images.
- **Automated Publishing**: Uses Playwright (via `xhs-kit`) to publish notes directly.
- Supports QR code login and session persistence (`cookies.json`).
- Prevents duplicate publishing.

## 🛠️ Prerequisites

- **Python 3.8+**
- **Playwright** (for Xiaohongshu automation & NewRank crawling)
- **DashScope API Key** (for Qwen LLM & Image generation)
- **WeChat Official Account App ID & Secret** (for WeChat syncing)

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd media_skills
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers**:
    ```bash
    playwright install chromium
    ```

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

```env
# DashScope (Aliyun Qwen)
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# WeChat Official Account
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# Xiaohongshu (Optional, can be passed via args)
# XHS_ALLOW_NON_HEADLESS=1 # Set to 1 to see browser interaction
```

## 📖 Usage

### 1. Crawl Hot Topics (NewRank)

Run the crawler to fetch trending topics:

```bash
python -m newrank_skill.crawler
```
*Output: `output/articles/*.json` (Individual article files)*

### 2. Generate & Sync to WeChat

Generate articles from the crawled data (supports single file or directory) and sync to WeChat Draft Box:

```bash
# Process all articles in the output directory
python wechat_skill/main.py --input output/articles --sync

# Process a single file
python wechat_skill/main.py --input output/articles/20240101_ArticleTitle.json --sync
```

**Options:**
- `--sync`: Upload to WeChat Draft Box.
- `--dry-run`: Generate only, do not save or upload.
- `--image-model`: Specify image model (default: `qwen-image-max`).
- `--no-ai-cover`: Skip AI cover generation.

### 3. Generate & Publish to Xiaohongshu

Generate notes from the crawled data (supports single file or directory) and publish them:

```bash
# Process all articles in the output directory
python xiaohongshu_skill/main.py --input output/articles

# Process a single file
python xiaohongshu_skill/main.py --input output/articles/20240101_ArticleTitle.json
```

**Options:**
- `--non-headless`: Run browser in visible mode (useful for debugging/login).
- `--dry-run`: Generate content only.
- `--model`: Specify LLM model (default: `qwen-plus`).
- `--no-cover`: Skip cover image generation.

**Login Note:**
On the first run, if not logged in, the script will generate a `login_qrcode.png`. Scan this with your Xiaohongshu App to login. Session cookies are saved to `cookies.json`.

## 📁 Project Structure

```
media_skills/
├── newrank_skill/       # NewRank Crawler
├── wechat_skill/        # WeChat Content Generator & Syncer
├── xiaohongshu_skill/   # Xiaohongshu Generator & Publisher
├── tests/               # Unit Tests
├── output/              # Generated artifacts
├── .env                 # Configuration (Git-ignored)
├── requirements.txt     # Dependencies
└── README.md            # Documentation
```

## 🛡️ Deduplication

Both WeChat and Xiaohongshu skills employ a local SQLite database (`wechat_published.db`, `xiaohongshu_published.db`) to track published titles. This prevents accidental duplicate posts of the same content.

## 📄 License

[MIT License](LICENSE)
