# Media Skills Collection

本仓库包含用于媒体内容获取、处理和发布的 Skill 集合。

## 1. NewRank Crawler (newrank_skill)

### 描述
此 Skill 用于抓取 NewRank 热点专题页面 (https://www.newrank.cn/hotInfo?module=hotSubject)，以获取热门文章及其内容。

### 功能
- 抓取 "热点专题" 板块。
- 提取文章元数据：标题、作者、发布时间、阅读数、点赞数。
- 提取完整的文章内容（摘要和正文）。
- 将数据保存为 JSON 格式。

### 用法
#### 运行爬虫
```bash
python -m newrank_skill.crawler
```

或者在你的 Python 代码中使用它：
```python
from newrank_skill.crawler import NewRankCrawler

crawler = NewRankCrawler(output_file="my_data.json")
crawler.run()
```

---

## 2. 小红书内容生成与发布 (xiaohongshu_skill)

### 描述
此 Skill 用于将长文章转换为小红书风格的笔记（Emoji 风格，<1000字），并通过 MCP 服务发布。

### 功能
- **内容生成**：基于 Qwen (千问) 将长文章压缩、提炼核心要点、添加 Emoji 和标签。
- **发布**：将生成的笔记通过 HTTP API (MCP) 发布到小红书账号。

### 前置条件
- 设置 `DASHSCOPE_API_KEY` (推荐) 或 `OPENAI_API_KEY` 环境变量。
- 确保小红书 MCP 服务正在运行（默认地址 `http://localhost:8000/api/publish`）。

### 用法

#### 命令行工具
主脚本 `xiaohongshu_skill/main.py` 支持多种输入方式。

1. **从 JSON 文件处理（如 NewRank 爬虫的输出）**:
   ```bash
   python xiaohongshu_skill/main.py --input newrank_hot_subjects.json
   ```

2. **从文本文件处理**:
   ```bash
   python xiaohongshu_skill/main.py --input article.txt --title "我的文章标题"
   ```

3. **仅生成内容（不发布）**:
   ```bash
   python xiaohongshu_skill/main.py --input article.txt --dry-run
   ```

4. **模拟发布（测试流程）**:
   ```bash
   python xiaohongshu_skill/main.py --input article.txt --mock
   ```

5. **指定 MCP 服务地址**:
   ```bash
   python xiaohongshu_skill/main.py --input article.txt --mcp-url http://my-mcp-service:8080/publish
   ```

#### 代码调用

```python
from xiaohongshu_skill import ContentGenerator, XiaohongshuPublisher

# 1. 生成内容
generator = ContentGenerator()
note = generator.generate_note(article_content, article_title)
print(note.title)
print(note.content)

# 2. 发布
publisher = XiaohongshuPublisher(service_url="http://localhost:8000/api/publish")
publisher.publish(note)
```

## 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```
