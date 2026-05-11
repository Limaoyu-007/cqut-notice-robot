# CQUT Notice Robot

重庆理工大学校园通知机器人。它会定时抓取学校官网通知，解析正文和附件，再用 AI 结合个人画像判断通知与你的相关性，最后通过飞书推送给用户。

这个项目已经正式上线运行，适合两类场景：

- 你是 CQUT 学生，想少刷官网，但不错过和自己有关的通知。
- 你想部署一个自己的校园通知监控机器人，并按自己的专业、年级和兴趣方向定制 AI 判断逻辑。

## 加入通知群

如果你只是想接收通知，可以扫描二维码加入飞书群：

<img src="assets/feishu_qr.png" width="250px" alt="飞书群二维码">

## 功能特性

- **多栏目抓取**：默认监控重庆理工大学官网多个通知栏目，包括部门通知、学校通知、招标信息、学术讲座等。
- **浏览器模拟访问**：基于 `DrissionPage` 启动 Chromium，适配需要真实浏览器环境的页面。
- **通知详情解析**：从详情页提取标题、发布时间、正文内容和附件链接。
- **AI 个性化解读**：根据用户画像判断通知的重要程度、相关度、关键时间、行动建议和关注理由。
- **推送分层**：高重要通知详细推送，中重要通知简短推送，低重要通知进入每日摘要。
- **每日摘要**：每天固定时间汇总当天通知，减少低价值消息打扰。
- **关键词兜底**：AI 不可用时，根据竞赛、实习、教务、招标等关键词进行基础判断。
- **用户画像外置**：支持通过 JSON 文件配置个人画像，不需要直接修改代码。
- **飞书实时推送**：通过飞书机器人 Webhook 推送格式化后的通知消息。
- **去重存储**：使用 SQLite 记录已处理通知，避免重复推送。
- **错误告警**：任务异常或推送失败时，可自动向飞书发送错误提醒。
- **本地预览**：支持 `--dry-run`，可在不写数据库、不推送飞书的情况下预览消息内容。

## 推送内容示例

启用 AI 后，一条通知会被整理成类似下面的结构：

```text
📢 【高重要】关于组织某项竞赛报名的通知

🧠 AI 解读
相关度：88/100
为什么值得看：这条通知和竞赛经历、项目实践直接相关，可能对简历有价值。
推荐处理：建议今天内查看原文，确认报名条件、截止时间和附件要求。

🎯 重点关注
1. 是否面向本科生开放
2. 是否有明确报名截止时间
3. 是否需要提交报名表或作品

⏰ 关键时间
发布时间：2026-05-10
截止时间：2026-05-20

🔗 原文链接
https://www.cqut.edu.cn/...
```

如果未配置 AI，机器人会推送官网原文、附件和原文链接。

## 快速开始

### 1. 准备环境

建议使用 Python 3.9 或更高版本。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

如果你在 Linux 或 macOS 上运行，激活虚拟环境的命令通常是：

```bash
source .venv/bin/activate
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

Linux 或 macOS：

```bash
cp .env.example .env
```

然后按需填写：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-token

AI_API_KEY=your-api-key
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
AI_MODEL=deepseek-v4-flash
AI_ENABLED=true
USER_PROFILE_PATH=profiles/cs_student.json

SCHEDULE_INTERVAL_MINUTES=10
REQUEST_TIMEOUT=15
BROWSER_PATH=
NOTICE_ROBOT_LOG_PATH=logs/notice_robot.log
ERROR_ALERT_ENABLED=1
DRY_RUN=false
```

### 3. 调整用户画像

AI 判断逻辑默认读取 [profiles/cs_student.json](profiles/cs_student.json)。你可以复制一份新的 JSON，并在 `.env` 中通过 `USER_PROFILE_PATH` 指向它：

- 专业和年级
- 求职或升学方向
- 高兴趣通知类型
- 低兴趣通知类型
- 高、中、低重要度判断规则

这一步决定了 AI 会如何回答“这条通知是否值得我现在停下来查看”。

### 4. 预览运行

第一次建议先 dry-run：

```bash
python main.py --dry-run
```

dry-run 会抓取并解析当前通知，在终端输出飞书消息预览，但不会写入数据库，也不会真的推送到飞书。

如果你希望通过配置长期启用预览模式，也可以在 `.env` 中设置：

```env
DRY_RUN=true
```

这和命令行 `--dry-run` 效果一致：程序只执行一轮预览，然后退出，不进入定时循环。

### 5. 正式运行

```bash
python main.py
```

程序会先立即执行一轮抓取，之后按照 `SCHEDULE_INTERVAL_MINUTES` 设置的间隔循环运行。

## 配置说明

| 配置项 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `FEISHU_WEBHOOK_URL` | 是 | 空 | 飞书机器人 Webhook。未配置时不会成功推送。 |
| `AI_ENABLED` | 否 | `true` | 是否启用 AI 解读。 |
| `AI_API_KEY` | 启用 AI 时必填 | 空 | AI 服务 API Key。 |
| `AI_API_BASE_URL` | 否 | DashScope 兼容接口 | OpenAI-compatible Chat Completions 接口地址。 |
| `AI_MODEL` | 否 | `deepseek-v4-flash` | 使用的模型名称。 |
| `USER_PROFILE_PATH` | 否 | 空 | 用户画像 JSON 文件路径；为空时使用 `config.py` 内置画像。 |
| `SCHEDULE_INTERVAL_MINUTES` | 否 | `10` | 定时抓取间隔，单位分钟。 |
| `REQUEST_TIMEOUT` | 否 | `15` | 页面抓取超时时间，单位秒。 |
| `BROWSER_PATH` | 否 | 空 | Chromium 或 Edge 浏览器路径；为空时由 DrissionPage 自动查找。 |
| `NOTICE_ROBOT_LOG_PATH` | 否 | `logs/notice_robot.log` | 日志文件路径。 |
| `ERROR_ALERT_ENABLED` | 否 | `1` | 是否开启异常告警，`0` 表示关闭。 |
| `DRY_RUN` | 否 | `false` | 是否启用预览模式；开启后不写数据库、不推送飞书，只执行一轮后退出。 |
| `NOTICE_LIST_URLS` | 否 | 内置 CQUT 通知栏目 | 逗号分隔的通知列表页 URL。 |

## 项目结构

```text
.
├── main.py              # 程序入口、定时任务和主流程编排
├── config.py            # 环境变量、通知源、用户画像和 AI 配置
├── crawler.py           # DrissionPage 浏览器抓取
├── parser.py            # 列表页和详情页 HTML 解析
├── ai_analyzer.py       # AI 提示词构建、接口调用和 JSON 结果解析
├── push_policy.py       # 根据 AI 结果决定推送方式
├── daily_digest.py      # 每日摘要格式化
├── keyword_classifier.py # AI 不可用时的关键词兜底判断
├── notifier.py          # 飞书消息格式化与发送
├── error_notifier.py    # 异常消息格式化与告警
├── db.py                # SQLite 持久化和去重
├── models.py            # Notice、Attachment、AIAnalysis 数据结构
├── logger_setup.py      # 日志初始化
├── profiles/            # 用户画像 JSON 配置
├── tests/               # 单元测试
├── assets/              # README 图片资源
└── data/                # 运行时数据目录
```

## 运行机制

一次完整任务大致如下：

```text
读取配置
  ↓
抓取多个通知列表页
  ↓
解析通知标题、链接、时间和栏目
  ↓
根据 URL 在 SQLite 中去重
  ↓
抓取新通知详情页
  ↓
解析正文和附件
  ↓
可选：调用 AI 生成个性化解读
  ↓
根据重要度选择详细推送、简短推送或仅进入摘要
  ↓
发送飞书消息或等待每日摘要
  ↓
写入数据库并导出 JSON
```

## 推送策略

机器人会根据 AI 结果决定推送方式：

| 重要度 | 推送方式 |
| --- | --- |
| `high` | 立即详细推送 |
| `medium` | 立即简短推送 |
| `low` | 不立即打扰，进入每日摘要 |
| AI 不可用 | 使用关键词规则兜底，无法判断时推送原文 |

低重要通知仍会写入数据库，并在每日摘要里出现，因此不会被丢弃。

## 数据与日志

运行后会生成这些文件：

- `data/notices.db`：SQLite 数据库，用于记录已处理通知。
- `data/notices.json`：通知数据导出，方便查看和备份。
- `logs/notice_robot.log`：运行日志，包含抓取、解析、推送和异常信息。

这些运行时文件默认不会提交到 Git。

## 测试

```bash
python -m unittest discover tests
```

当前测试覆盖了：

- 配置加载和密钥安全检查
- 通知列表合并与去重
- 详情页正文、日期和附件解析
- AI JSON 结果标准化
- 飞书消息格式化
- SQLite 数据往返
- 推送策略和每日摘要
- 关键词兜底分类
- 日志和错误告警

## 部署建议

你可以用任意长期运行方式部署它，例如：

- Windows 任务计划程序
- Linux `systemd`
- `tmux` / `screen`
- Docker 或服务器常驻进程

部署时建议：

- 抓取间隔不要过短，默认 10 分钟已经足够。
- 确认服务器上有可用的 Chromium、Chrome 或 Edge。
- 先用 `--dry-run` 验证抓取和消息格式。
- 不要把 `.env`、数据库和日志文件提交到公开仓库。

## 后续计划

- 发送失败后的重试队列，避免“入库成功但推送失败”导致漏通知。
- 支持更多学校或学院通知源。
- 增加 Web 管理页，用于查看历史通知和调整用户画像。
- 增加 Docker 部署模板。

## 免责声明

本项目仅供学习、研究和个人使用。请遵守重庆理工大学官网的访问规则和 `robots.txt` 协议，不要高频请求、恶意抓取或用于商业用途。使用者需要自行承担部署、配置和消息推送带来的风险。
