# Media Skills Automation Project

This project automates content creation and publishing for **Xiaohongshu (Little Red Book)**. It integrates AI-powered generation (text & images) and automated publishing capabilities.

## 🚀 Features

### Xiaohongshu Automation (`xiaohongshu_skill`)
- Generates lifestyle notes (text + emoji + tags) suitable for Xiaohongshu.
- Generates cover images using AI or templates.
- **Automated Publishing**: Uses Playwright (via `xhs-kit`) to publish notes directly.
- Supports QR code login and session persistence (`cookies.json`).

## 🛠️ Prerequisites

- **Python 3.8+**
- **Playwright** (for browser automation)
- **DashScope API Key** (for Qwen LLM & Image generation)

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

Create a `.env` file in the project root (see `.env.example`):

```env
# DashScope (Aliyun Qwen)
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Xiaohongshu (Optional)
# XHS_ALLOW_NON_HEADLESS=1 # Set to 1 to see browser interaction
```

## 📖 Usage

### Generate & Publish to Xiaohongshu

Generate notes from input data (supports single file or directory) and publish them:

```bash
# Process all articles in the output directory
python xiaohongshu_skill/main.py --input output/articles

# Process a single file
python xiaohongshu_skill/main.py --input output/articles/20240101_ArticleTitle.json
```

**Options:**
- `--non-headless`: Run browser in visible mode (useful for debugging/login).
- `--dry-run`: Generate content only, do not publish.
- `--model`: Specify LLM model (default: `qwen-plus`).
- `--no-cover`: Skip cover image generation.

**Login Note:**
On the first run, if not logged in, the script will generate a `login_qrcode.png`. Scan this with your Xiaohongshu App to login. Session cookies are saved to `cookies.json`.

### Launcher (Menu Interface)

You can use the interactive launcher for easier operation:

```bash
python launcher.py
```
Or double-click `run.bat` on Windows.

## 📁 Project Structure

```
media_skills/
├── xiaohongshu_skill/   # Xiaohongshu Generator & Publisher
├── tests/               # Unit Tests
├── output/              # Generated artifacts
├── .env                 # Configuration (Git-ignored)
├── requirements.txt     # Dependencies
└── README.md            # Documentation
```

## 📄 License

[MIT License](LICENSE)
