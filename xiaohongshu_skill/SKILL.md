---
name: xiaohongshu-creator
description: 自动生成和发布小红书（RedNote）风格的图文笔记。擅长将长文章、新闻或技术内容转化为Emoji丰富、排版精美、标题吸引人的种草/科普笔记。支持自动生成纯文字封面图和发布到MCP服务。
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash
---

# 小红书内容创作助手

## ⚠️ 核心风格规范

### 1. 标题（Title）
- **极度吸引眼球**：使用"爆款"标题公式（如：深夜emo...、家人们谁懂...、干货满满...）。
- **Emoji装饰**：标题必须包含1-2个Emoji。
- **长度限制**：控制在20字以内，但在封面图中会更短。

### 2. 正文（Content）
- **Emoji浓度高**：每段话、每个列表项都应有Emoji点缀。
- **排版清晰**：使用空行分隔段落，多用列表（bullet points）。
- **口语化/亲切**：称呼读者为"宝子们"、"家人们"、"集美们"（视语境而定）。
- **标签（Tags）**：文末必须包含5-10个相关标签（如 #小红书 #干货 #AI）。
- **字数**：控制在800字以内，太长没人看。

### 3. 封面（Cover）
- **纯文字/高对比度**：使用高饱和度背景色（如克莱因蓝、荧光绿）+ 大字标题。
- **重点突出**：封面标题要比文章标题更短、更冲击（如：3秒学会！、全网首发！）。

---

## 完整工作流程

### 步骤1：获取素材
当用户提供链接或主题时：
1. 使用 `WebSearch` 或 `WebFetch` 获取原始内容。
2. 提取核心观点、干货知识点或情感价值点，放到`article.txt`。

### 步骤2：内容转化与发布

使用 `xiaohongshu_skill` 中的工具链进行处理。推荐使用命令行工具 `main.py`。

运行命令读取文件：

```bash
python xiaohongshu_skill/main.py --input article.txt --title "笔记标题"
```

该脚本会自动：
1. 调用 `ContentGenerator` 将内容改写为小红书风格（Emoji、标签）。
2. 调用 `CoverGenerator` 生成高对比度文字封面。
3. 调用 `XiaohongshuPublisher` 发布到小红书（默认行为）。
   - 如果只想生成不发布，请添加 `--dry-run` 参数。
   - 如果需要看到浏览器界面（调试/扫码），请添加 `--non-headless` 参数。

### 步骤3：检查与发布
- 检查生成的 `output/` 目录下的 JSON 和图片。
- 确认发布结果（脚本会自动输出 "✅ Successfully published"）。

---

## 常用指令示例

- "把这篇关于DeepSeek的文章改成小红书笔记发布" -> 爬取 -> `main.py`
- "用小红书风格写一篇Python入门教程" -> 生成内容 -> 保存为txt -> `main.py`
