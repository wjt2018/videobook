# VideoBook Agent 工作流指令

> 本文件是 AI 助手（Antigravity / Claude Code）的操作手册。
> 当用户发来一个视频链接时，请严格按照以下步骤执行。

## 触发条件

用户发来一条包含 YouTube (`youtube.com`, `youtu.be`) 或 B站 (`bilibili.com`) 视频链接的消息，
并表示希望将其生成为电子书/教程/指南。

## 完整工作流

### 第一步：提取字幕

在终端执行以下命令（将 `<VIDEO_URL>` 替换为用户提供的链接）：

```bash
python dump_transcript.py "<VIDEO_URL>"
```

- 脚本会自动检测平台，抓取字幕并保存为 `output/<video_id>/transcript.json`。
- 如果失败，请告知用户可能的原因（无字幕、需要代理、需要 Cookie 等），并停止流程。

### 第二步：阅读字幕 + 生成电子书

1. 阅读生成的 `output/<video_id>/transcript.json` 文件。
2. 阅读 `prompts/stitcher_system.md` 获取排版指令。
3. 按照 Stitcher Prompt 的要求，将字幕重构为结构化的 Markdown 技术指南。
4. 将生成的内容写入 `output/<video_id>/book.md`。

**关键要求：**
- 必须将口语化内容转为书面化技术语言
- 必须分章节组织，使用 Markdown 标题
- 必须在关键界面/操作步骤处插入截图占位符：`![场景描述](SCREENSHOT:HH:MM:SS)`
- 如果原始语言不是中文，必须翻译为中文

### 第三步：转换 HTML + 启动预览

在终端依次执行以下命令：

```bash
python post_process.py "<VIDEO_URL>" output/<video_id>/book.md
python -m http.server 8080 --directory output/<video_id>
```

### 第四步：告知用户

将以下信息回复给用户：

1. ✅ 电子书 Markdown 文件位置：`output/<video_id>/book.md`
2. ✅ HTML 电子书预览地址：**http://localhost:8080/book.html**
3. 提醒用户：
   - 如果是 YouTube 视频，请确保浏览器可以访问 YouTube（需要代理）
   - 如果是 B 站视频，可以直接访问
   - 关闭预览服务器：在终端按 `Ctrl+C`

## 注意事项

- 工作目录始终是 `d:\my\videobook`
- 所有 Python 命令使用 `python` 执行（不要用 `pip`，用 `python -m pip`）
- 所有外部工具（yt-dlp）通过 `sys.executable -m yt_dlp` 调用
- 如果用户提供的是 YouTube 链接且终端无代理，字幕抓取可能会失败
- 在生成或修改 HTML 时，请确保文本颜色与背景颜色的对比度符合 WCAG AA 标准（对比度至少 4.5:1）。
