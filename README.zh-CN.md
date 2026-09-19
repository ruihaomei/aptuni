<p align="center"><img src="assets/brand/logo/aptuni-icon.svg" width="120" alt="Aptuni"></p>

<h1 align="center">Aptuni</h1>
<p align="center"><b>越用，越懂你。</b></p>
<p align="center">个人上下文 · 记忆 · MCP · 本地优先</p>
<p align="center"><a href="README.md">English</a> · <a href="LICENSE">Apache-2.0</a> · 预览版（pre-alpha）</p>

**Aptuni 把恰到好处的“你”提供给你的 AI 智能体，而不是把关于你的一切都交出去。**
它是一个会随着使用逐渐更懂你的个人上下文层。

你不必再向每个智能体反复介绍自己。智能体只会拿到与当前任务相关、可核查的一小部分信息，
而全部数据以开放格式保存在你自己的设备上。

> **状态：预览版（里程碑 1）。** 核心功能已在 macOS 上端到端可用，接口仍可能变化。
> 参见[当前可用功能](#当前可用功能)与[路线图](docs/dev/ROADMAP.md)。

## 为什么选择 Aptuni

- **重在契合，而非堆积。** 智能体只获得完成任务所需的最小上下文，而不是你的全部资料。
- **数据归你所有。** Profile Vault 是你磁盘上的普通 JSONL/Markdown 文件；索引和记忆引擎都可以重建，
  更换后端不会让你“丢失自己”。
- **只认证据，不做臆断。** 文档里提到 XGBoost 只算“接触过”（exposure），不等于掌握。每条结论都保留来源、时间和历史。
- **开关在你手里。** 每个模块（知识、经历、偏好……）都有独立的“写入”与“对智能体可见”开关。
  “别把我的工作经历告诉智能体”只会隐藏，不会删除。
- **无需额外 API 密钥。** 默认配置不需要 Docker、向量数据库、图数据库或模型密钥；
  你已经在用的 Claude Code 或 Codex 就可以提供智能。

## 让智能体帮你安装

在 Claude Code 或 Codex 中打开本仓库，然后说：

> 阅读这个仓库，帮我配置好 Aptuni。

智能体会阅读 [`AGENTS.md`](AGENTS.md)，先询问你使用哪种语言，再通过 `aptuni advise` 了解：
你有哪些资料来源、希望它如何记住你、个人数据能否交给云端模型处理。安装任何东西之前，
它都会先展示方案，包括 API 密钥、配置时间、隐私影响与取舍。

## 60 秒手动上手

需要 Python 3.13 和 [uv](https://docs.astral.sh/uv/)。

```sh
git clone <本仓库地址> aptuni && cd aptuni
uv sync
uv run aptuni advise --lang zh-CN        # 回答几个简单问题；不会修改任何内容
uv run aptuni init ~/Aptuni              # 创建你的 Profile Vault
uv run aptuni remember "偏好简洁、结构化的技术解释。" --module preferences
uv run aptuni source add-folder ~/Documents/简历 --module experience --role application-materials
uv run aptuni sync SOURCE_ID             # 从你批准的文件中提取最小化证据
uv run aptuni context "帮我准备数据科学面试" --module experience --evidence --budget 1500
```

然后连接智能体：

```sh
uv run aptuni adapter plan claude --module identity --module preferences --allow-host-model-egress
uv run aptuni adapter apply ACTION_ID    # 在你自己的终端里确认
```

## 当前可用功能

| 功能 | 状态 |
|---|---|
| Profile Vault：事实、历史、更正、崩溃安全写入、`doctor` | ✅ |
| 模块权限（写入 / 可见，相互独立） | ✅ |
| 文件夹来源（Markdown、纯文本、CSV），增量同步并保留来源 | ✅ |
| GitHub 来源（标准模式，有界读取，精确到提交） | ✅ |
| 中英文本地检索，索引可随时重建 | ✅ |
| 分层上下文（L0 身份卡 → L4 证据），带预算 | ✅ |
| 本地 STDIO 的 MCP 服务：权限受控读取与隔离的记忆提案 | ✅ |
| Claude Code 与 Codex 适配器 | ✅ |
| 插件顾问、配方、中英文命令行 | ✅ 预览（`aptuni advise`） |
| MarginNote 4 来源（macOS，本地只读直连，原生 ID） | ✅ |
| Obsidian 来源与界面、Mem0、混合检索、Graphiti | 🗺 里程碑 2–3 |

运行 `aptuni plugin list --lang zh-CN` 和 `aptuni recipe list --lang zh-CN` 可以在命令行看到同样的信息。

## 工作原理

```text
资料来源 ──► 证据 ──► 档案 + 记忆 ──► 上下文 ──► 智能体
(文件夹、    (最小化、   (时间化事实、   (L0–L4、    (MCP、Claude Code、
 GitHub、     可溯源)     你的开关)       有预算)      Codex)
 MarginNote)
```

- **档案 ≠ 记忆 ≠ 上下文。** 档案变化慢，记忆形成快；上下文是运行时为具体任务组装的一小部分。
- **渐进披露。** 智能体先拿到一张简短的身份卡，只有任务需要时才进一步读取。
- **资料变化是安全的。** 每次同步都是不可变快照加可审阅的变更；删除文件只会撤回证据，
  不会悄悄改写历史；有歧义的变化会等你确认。

设计决策见 [`docs/dev/DECISIONS/`](docs/dev/DECISIONS/README.md)，产品需求见
[`docs/product/PRD.md`](docs/product/PRD.md)。

## 配方

| 配方 | 适合 | 需要 |
|---|---|---|
| **轻量入门** | 开箱即用 | 无额外要求 |
| **研究者** | 把笔记、文档和代码作为知识证据 | 可选 `GITHUB_TOKEN` |
| 个人记忆 | 从日常对话中学习 | 里程碑 2（Mem0） |
| 时序记忆 | 随时间变化的关系 | 里程碑 3（Graphiti） |

你选择想要的体验，Aptuni 负责选择组件。暂不可安装的配方会给出最接近且可用的替代方案。

## 隐私概要

Aptuni 不会主动扫描你的电脑；发现某个来源并不等于获得读取许可。默认不保存原始对话。
智能体只能在预算内看到你开放的模块；适配器预览会明确告诉你哪些数据会离开本机
（例如，智能体读取的上下文会由该智能体的模型提供方处理）。详见 [`SECURITY.md`](SECURITY.md)
与[威胁模型](docs/dev/THREAT_MODEL.md)。

## 参与贡献

欢迎贡献插件、配方、翻译和问题报告，请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
向插件顾问添加一个插件只需要一个 TOML 文件和两行消息文本。

## 许可证

[Apache-2.0](LICENSE)。第三方声明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
