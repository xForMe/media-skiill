# Media Skills Collection

本仓库包含用于媒体内容获取、处理和发布的 Skill 集合。

## 1. NewRank Crawler (newrank_skill)

### 描述
此 Skill 用于抓取 NewRank 热点专题页面 (https://www.newrank.cn/hotInfo?module=hotSubject)，以获取热门文章及其内容。

### 功能
- **增量抓取**：自动过滤已抓取过的文章（基于 SQLite 去重）。
- **数据提取**：提取标题、作者、发布时间、阅读数、点赞数及正文。
- **数据存储**：将数据保存为 JSON 格式，供后续 Skill 使用。

### 用法
#### 运行爬虫
```bash
python -m newrank_skill.crawler
```
输出文件默认为 `newrank_hot_subjects.json`。

---

## 2. 微信公众号自动化 (wechat_skill)

### 描述
此 Skill 用于自动生成微信公众号文章并同步到后台草稿箱。

### 功能
- **智能写作**：基于 Qwen (通义千问) 模型，根据输入的主题或文章生成公众号风格内容。
- **封面生成**：支持使用 Qwen-VL 或 Wanx 生成配套封面图。
- **自动同步**：调用微信公众号 API 将文章和封面直接上传至草稿箱。
- **防重复**：本地记录已发布的文章标题，避免重复发送。

### 用法
#### 生成并同步
```bash
python wechat_skill/main.py --input newrank_hot_subjects.json --sync
```

#### 仅生成内容（不上传）
```bash
python wechat_skill/main.py --input newrank_hot_subjects.json --dry-run
```

#### 参数说明
- `--sync`: 同步到微信后台。
- `--no-ai-cover`: 不生成 AI 封面（使用纯色背景）。
- `--image-model`: 指定生图模型 (默认 `qwen-image-max`)。

---

## 3. 小红书内容生成与发布 (xiaohongshu_skill)

### 描述
此 Skill 用于将长文章转换为小红书风格的笔记，并利用浏览器自动化技术直接发布。

### 功能
- **爆款文案**：自动生成 Emoji 风格、包含标签的笔记内容。
- **自动发布**：集成 Playwright (基于 `xhs-kit`)，模拟浏览器行为进行发布。
- **登录持久化**：支持扫码登录，并自动保存 Cookie 实现免登。
- **防重复**：发布前检查本地记录，防止重复发布同一内容。

### 用法
#### 生成并发布
```bash
python xiaohongshu_skill/main.py --input newrank_hot_subjects.json
```

#### 首次登录/调试模式
如果需要扫码登录或查看浏览器操作，请添加 `--non-headless` 参数：
```bash
python xiaohongshu_skill/main.py --input newrank_hot_subjects.json --non-headless
```

#### 参数说明
- `--non-headless`: 显示浏览器界面（非无头模式）。
- `--dry-run`: 仅生成内容，不执行发布。
- `--no-cover`: 跳过封面生成。

---

## 安装与配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 环境配置
在项目根目录创建 `.env` 文件：

```env
# DashScope (阿里大模型)
DASHSCOPE_API_KEY=your_key_here

# 微信公众号 (用于 wechat_skill)
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
```
