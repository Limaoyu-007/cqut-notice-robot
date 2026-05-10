# CQUT Notice Robot (重庆理工大学通知机器人)

一个基于 AI 驱动的校园通知监控与分析助手，能够自动抓取重庆理工大学官网通知，并利用 AI 进行个性化重要程度判断，最后通过飞书推送给用户。

## 🌟 核心特性

- **自动化抓取**：基于 `DrissionPage` (Chromium) 模拟真实浏览器行为，稳定抓取学校官网各栏目通知。
- **AI 智能分析**：集成 AI 大模型（支持 DeepSeek 等），根据用户预设的身份画像（如专业、年级、兴趣方向）自动筛选通知，判定重要程度。
- **个性化推送**：根据 AI 分析结果展示“为什么值得看”、“关键时间点”和“行动建议”，告别信息过载。
- **飞书集成**：通过飞书 Webhook 实时推送图文消息。
- **去重机制**：使用 SQLite 数据库记录已处理通知，确保不重复推送。
- **容错设计**：内置错误告警逻辑，任务失败时自动向管理员发送异常信息。

## 🛠️ 项目结构

- `main.py`: 程序入口，负责调度流程与定时任务。
- `crawler.py`: 网页抓取模块，处理浏览器环境仿真。
- `parser.py`: HTML 解析模块，提取通知正文、日期及附件。
- `ai_analyzer.py`: AI 处理模块，调用大模型进行内容提炼。
- `db.py`: 数据持久化，防止重复抓取。
- `notifier.py`: 飞书消息格式化与发送。
- `config.py`: 项目配置中心（UA、URL、AI 提示词等）。

## 🚀 快速开始

### 📸 扫码入群
如果你对本项目感兴趣，欢迎扫描下方二维码加入飞书群讨论：

<img src="assets/feishu_qr.png" width="250px" alt="飞书群二维码">

### 1. 环境准备
确保已安装 Python 3.9+，并安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置信息
在项目根目录创建 `.env` 文件（参考 `.env.example`）：
```env
# 飞书 Webhook
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# AI 配置 (可选)
AI_ENABLED=true
AI_API_KEY=your_api_key
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
AI_MODEL=deepseek-v4-flash

# 用户画像设置 (在 config.py 中调整自定义身份)
```

### 3. 运行项目
直接启动程序进入定时监控模式（默认每 10 分钟检查一次）：
```bash
python main.py
```

如果你只想预览当前的通知而不发送飞书消息，可以使用：
```bash
python main.py --dry-run
```

## 🧪 测试
本项目包含完整的单元测试，可以使用以下命令运行：
```bash
python -m unittest discover tests
```

## ⚖️ 免责声明
本项目仅供学习和个人使用，请务必遵守学校官网的 robots.txt 协议，严禁用于高频攻击或商业用途。
