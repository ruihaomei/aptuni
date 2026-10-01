<p align="center"><img src="https://raw.githubusercontent.com/ruihaomei/aptuni/v0.2.0b9/assets/brand/logo/aptuni-icon.svg" width="120" alt="Aptuni"></p>

<h1 align="center">Aptuni</h1>
<p align="center"><b>越用，越懂你。</b></p>
<p align="center">个人上下文 · 记忆 · MCP · 本地优先</p>
<p align="center"><a href="https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/README.md">English</a> · <a href="https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/LICENSE">Apache-2.0</a> · v0.2.0b9 Beta 版</p>

**Aptuni 把恰到好处的“你”提供给你的 AI 智能体，而不是把关于你的一切都交出去。**
它是一个会随着使用逐渐更懂你的个人上下文层。

你不必再向每个智能体反复介绍自己。智能体只会拿到与当前任务相关、可核查的一小部分信息，
而全部数据以开放格式保存在你自己的设备上。

> **状态：Beta（0.2.0b9）。** 核心、智能体激活与插件平台已在受支持的 macOS 与 Ubuntu 24.04/ext4
> 系统上端到端可用，Top-Down Learning 作为 1 号旗舰插件随版本发布。正式版之前接口仍可能变化。参见[当前可用功能](#当前可用功能)与
> [路线图](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/docs/dev/ROADMAP.md)。

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

把下面这句话粘贴给 Claude Code 或 Codex：

> 帮我安装并配置 Aptuni：运行 `uv tool install aptuni==0.2.0b9`（如果没有 uv 就先装 uv），然后运行
> `aptuni guide agent --lang zh-CN` 并按它的步骤来。

智能体会在聊天里问你几个问题——使用的语言、希望 Aptuni 了解你的哪些部分、个人数据能否交给云端模型处理、
要连接哪些智能体、是否需要 Top-Down Learning 插件——并自己运行所有命令。你只需要在自己的终端里输入一条
命令 `aptuni setup apply ACTION_ID`，再输入 `APPLY`：智能体永远不能替你批准对你数据的访问。之后智能体会
帮你连接 Claude Code 或 Codex，并告诉你如何使用；在你为某个任务打开之前，Aptuni 始终保持关闭。

### 或者自己在终端里配置

使用 Python 3.13 和 [uv](https://docs.astral.sh/uv/) 安装公开软件包：

```sh
uv tool install aptuni==0.2.0b9
aptuni --version
```

然后在终端运行引导式配置，回答几个问题即可：

```sh
aptuni setup plan
```

它会先问你使用哪种语言，用三句话说明 Aptuni 保存什么（Profile、Memory、证据），再问你希望
Aptuni 从哪些方面了解你：本地文件夹、Obsidian、GitHub、Notion 或 MarginNote。直接回车可以全部跳过，
以后随时能再添加。你选中的每个信息源，它会立刻询问具体的文件夹或仓库。Notion 和 MarginNote 需要
浏览器授权或 macOS 权限确认，所以计划里会列出之后要运行的准确命令。在你用
`aptuni setup apply ACTION_ID` 确认计划并输入 `APPLY` 之前，不会创建任何东西。


你也可以自己执行同一套流程。只要两条命令；第一条只创建一份私有、会过期的方案记录，
不会创建 Vault、来源、授权或宿主 bundle：

```sh
aptuni setup plan --lang zh-CN --folder ~/Documents/笔记 --host claude_code
aptuni setup apply ACTION_ID      # 由你在自己的终端输入 APPLY
```

`setup plan` 会打印推荐的组件及其理由、所需 API 密钥与配置时间、**智能体究竟能读取你的哪些模块
以及由哪家运营方接收**、将要读取的确切文件夹、**将要写入的每一个文件及其位置**，以及确切的步骤
顺序——然后停下。在你确认这一份方案之前不会发生上述任何效果；确认绑定该方案的摘要，因此被
改动过的方案永远无法被执行。

Aptuni 会把智能体集成写入它自己的目录，**不会**修改宿主自身的配置；需要你自行让宿主指向它。
若某一步失败，执行会就地停止，并可从断点续跑；某个来源暂时读取不了不会让它停下，结果中会列出该来源和重试命令。`aptuni setup cancel ACTION_ID` 会撤销它授予的
智能体访问权限，并如实告诉你还剩下什么——你的 Vault、来源和证据永远不会被替你删除。

## 已经有 Vault？（重装或换电脑）

Vault 是一个完全属于你的普通文件夹；Aptuni 保存的其他东西都是可以重建的本地状态。重装之后、
换到新电脑上，或者本地状态被删除时，请重新连接原来的 Vault，而不是新建一个：

```sh
aptuni attach ~/Aptuni            # 包含 HEAD.json 的那个文件夹
aptuni status
```

`attach` 只读取并校验 Vault，然后让当前安装指向它，Vault 里的任何内容都不会改动。遇到以下情况
它会拒绝并说明原因：所选文件夹不是 Vault、Vault 校验未通过，或者当前安装已经在使用另一个 Vault。
`aptuni setup plan --vault ~/Aptuni` 也会识别已有的 Vault，在计划中显示“使用你现有的 Profile
Vault”，而不是新建。授权和智能体集成属于本地状态，连接之后需要重新规划。

## 60 秒手动上手

需要先按上面的方式安装 Python 3.13 软件包。

```sh
aptuni advise --lang zh-CN        # 回答几个简单问题；不会修改任何内容
aptuni init ~/Aptuni              # 创建你的 Profile Vault（也可交给 `setup apply`）
aptuni remember "偏好简洁、结构化的技术解释。" --module preferences
aptuni source add-folder ~/Documents/简历 --module experience --role application-materials
aptuni sync SOURCE_ID             # 从你批准的文件中提取最小化证据
aptuni context "帮我准备数据科学面试" --module experience --evidence --budget 1500
```

然后连接智能体：

```sh
aptuni adapter plan claude --module identity --module preferences --allow-host-model-egress
aptuni adapter apply ACTION_ID    # 在你自己的终端里确认
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
| Obsidian 来源（识别仓库，把双链与属性名保留为结构） | ✅ |
| Notion 来源（官方 MCP，仅限明确页面/数据库） | ✅ |
| 规范 Vault 的可校验备份与恢复 | ✅ |
| Mem0 本地投影（`infer=False`，删除时重建整个存储） | ✅ 预览 |
| 显式混合检索（SQLite + 已接受记忆的 Mem0 排名） | ✅ 预览 |
| Obsidian 所有者评审界面 | ✅ 桌面端 |
| 旗舰插件：[Top-Down Learning](https://github.com/ruihaomei/aptuni/tree/v0.2.0b9/examples/plugins/top_down_learning)——从你已经会的地方出发，只学抵达目标真正需要的知识；学习上下文经你确认后，可在本地或云端 Agent 之间迁移 | ✅ Beta |
| Graphiti | 🗺 里程碑 3 |

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

设计决策见 [`docs/dev/DECISIONS/`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/docs/dev/DECISIONS/README.md)，产品需求见
[`docs/product/PRD.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/docs/product/PRD.md)。

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
（例如，智能体读取的上下文会由该智能体的模型提供方处理）。详见 [`SECURITY.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/SECURITY.md)
与[威胁模型](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/docs/dev/THREAT_MODEL.md)。

这几条命令让这一点变得具体：

```sh
aptuni privacy status                  # 列出 Aptuni 管理的每一份副本，以及它无法替你删除的那些
aptuni privacy purge preview <id>      # 预览这次删除会移除哪些记录和副本
aptuni privacy purge confirm <action>  # 不可逆，且只对这一份预览生效
aptuni privacy purge cancel <action>   # 放弃一次尚未删除任何内容的已确认清除
```

`privacy status` 会如实点名外部副本——你自己导出的文件、你的原始来源文件，以及由智能体提供方
保存的对话记录。Aptuni 删不掉它们，也不会假装删得掉。清除回执会逐份说明每一份副本的真实结果。

### 可选的 Mem0 投影预览

Mem0 只是由你在 Aptuni 中已接受记忆构建的本地派生投影；它不拥有 Profile 真相，也不会收到原始
对话。安装 `mem0` 可选依赖并运行本地 Ollama 嵌入模型后，可以显式管理这一投影：

```sh
aptuni memory provider status
aptuni memory provider rebuild
aptuni search "我该如何组织实验？" --hybrid
aptuni memory provider delete
```

重建始终使用 `infer=False`。隐私清除不依赖 Mem0 的单条删除，而是立即移除整个托管投影。忘记
记忆会把现有投影标为过期，并在下一次显式重建时排除已撤销记忆。设置流程和配方不会自动选择
这一预览功能。`search --hybrid` 只接受最新且已完成清理的投影，并且只合并排名位置；Mem0 分数
不会成为规范数据。默认检索与 Context API 仍使用内置 SQLite/FTS 路径。

预览阶段有两点需要留意。语义通道目前没有相关性下限，即使查询没有任何关键词命中，也可能返回
最多 `--limit` 条已接受记忆，请自行判断结果而不要直接采信。此外，返回的 `score` 只在同一次
调用内可比较：普通检索与 `--hybrid` 使用的是不同量纲。

## 把 Obsidian 仓库当作结构来读

Obsidian 仓库不只是一堆 Markdown 文件，因此 Aptuni 按图谱来读取它：

```sh
aptuni source add-obsidian ~/Vault --module knowledge
aptuni sync SOURCE_ID
aptuni evidence --source SOURCE_ID
```

只有包含 `.obsidian/` 的目录才算仓库，其他目录会被拒绝并提示改用 `add-folder`。仓库自身的
`.obsidian/` 配置与 `.trash/` 在任何读取之前就被排除，并且只打开 `.md` 文件——图片、PDF 等附件
只做计数，从不解析。

每条笔记贡献的是**结构**而不是正文：笔记名、所在文件夹、双链目标、标签与别名，以及 frontmatter
属性的**名称**。属性的**取值**保持私密：frontmatter 区块永远不作为摘录的来源，属性取值也不会进入存储的定位符，
因此日记里的 `employer:` 或 `salary:` 不会经由属性区块进入智能体的上下文。（若你同时把该取值写进
正文，被摘录的就是正文——任何来源都是如此。）代码块内的双链与标签不算结构，
不常见的 frontmatter 会被如实报告而不是猜测。详见
`docs/dev/DECISIONS/ADR-0017-obsidian-vault-source.md`。

## 在 Obsidian 中审阅 Aptuni

Obsidian 所有者界面与上面的来源插件完全分离：安装界面不会授予笔记摄取权，插件也不会
扫描或写入笔记。先把三个内置文件安装到已有的桌面端仓库，再在 Obsidian 的第三方插件
设置中由你自行启用 **Aptuni**：

```sh
aptuni interface obsidian install ~/Vault
```

从侧边栏打开 Aptuni，即可查看 Profile、Memory、Evidence、最近变更、待审阅项与晋升状态。
接受、编辑、拒绝、固定、忘记和查看证据都复用 Aptuni 现有的规范审阅规则；“忘记”一定先显示
绑定摘要的确认。插件只保存本地 Aptuni 可执行文件设置，不持久化返回的个人内容。如果 Obsidian
的 PATH 中找不到 `aptuni`，请在插件设置里填绝对路径。暂不支持 Obsidian 移动端。详见
`docs/dev/DECISIONS/ADR-0023-obsidian-owner-interface.md`。

## 通过官方 MCP 精确读取 Notion

Notion 只是可选来源，不是 Aptuni 的存储。先通过 Notion 官方托管 MCP 完成一次连接，再明确批准
真正需要摄取的页面或数据库：

```sh
aptuni source connect-notion
aptuni source add-notion https://www.notion.so/EXACT_PAGE_ID --module knowledge --role notes
aptuni sync SOURCE_ID
aptuni evidence --source SOURCE_ID
```

OAuth/PKCE 凭据只保存在 macOS 钥匙串中，Notion API 令牌不会进入 Vault 或状态目录。同步只检查
当前连接的 `self` 主体，再对这些精确根调用官方 `fetch`，不会搜索整个工作区、读取最近页面、
自动发现后代或调用写工具。Aptuni 保留
稳定的页面/数据库来源和一小段 Evidence 摘录，随后丢弃原始 MCP 响应。若响应被截断或含未知内容，
快照会标记为不完整，而不会撤回既有 Evidence。可用 `aptuni source disconnect-notion` 删除连接。
详见 `docs/dev/DECISIONS/ADR-0021-official-notion-mcp-source.md`。

## 它会自己学习，而不打断你

把关于你自己的事情告诉 Aptuni，不会因此多出一个必须逐条处理的队列：

```sh
aptuni observe "偏好确定性可复现的实验流水线。" --module knowledge
# 已记录并立即生效：mem_… —— 因为这是你自己说的，Aptuni 直接采用了它。
```

这条记忆立刻生效，并被标记为“Aptuni 自行添加”。你可以在方便的时候再回头审阅，而不必在它生效前审阅：

```sh
aptuni memory review list                  # 查看 Aptuni 自行学到的内容
aptuni memory review accept  MEMORY_ID     # 保留
aptuni memory review edit    MEMORY_ID "…" # 修正；原记录保留在历史中
aptuni memory review reject  MEMORY_ID     # 停止使用
aptuni memory review pin     MEMORY_ID     # 保留，并不再提醒
```

有三类情况仍然**先询问再生效**：由智能体而非你本人提出的内容、敏感模块（默认为 `identity`、
`relationships`、`behavior`）中的内容，以及与仍然有效的记录相互矛盾的内容。它们保留输入确认的流程。

提醒只是一行文字，不是弹窗——默认在积压十条或满十五天时出现（以先到者为准），
`aptuni memory review snooze` 可以推迟。用
`aptuni memory review policy --auto-promotion off` 可以完全关闭该功能。详见
`docs/dev/DECISIONS/ADR-0018-automatic-promotion-and-retrospective-review.md`。

## 持续衡量自己的真实配置

所有者可以针对普通 Context 路径运行一套私密、可重复的长期体验评估：

```sh
aptuni evaluate setup
aptuni evaluate trial "智能体在这个任务里应该了解我的哪些信息？"
aptuni evaluate score TRIAL_ID --useful ID... --noise ID...
aptuni evaluate capture
aptuni evaluate report
```

本地状态只保留查询摘要、规范记录 ID、显式标签和不含正文的指标；查询原文和返回的上下文不会持久化。
报告覆盖有用性/噪声、缺少支持的有用结果、来源覆盖、暴露权限、来源更新、晋升/审阅状态和上下文单位效率。
`aptuni evaluate reset` 会删除整套派生评估数据。

## 真正能恢复的备份

`aptuni export` 写出的是当前 Profile 的可读副本，它用于阅读，无法用于恢复。可恢复的副本是备份：

```sh
aptuni backup create ~/aptuni-backups/2026-09-20   # 一份经过校验的副本，存放在 Vault 之外
aptuni backup verify ~/aptuni-backups/2026-09-20   # 校验它，同时不触碰你的 Vault
aptuni backup list   ~/aptuni-backups              # 你有哪些备份，以及它们是否仍然通过校验
aptuni backup restore preview <path>               # 恢复会替换、丢弃和保留什么，逐项列出
aptuni backup restore confirm <action>             # 只对这一份预览生效
```

备份是你规范记录的完整未加密副本，包含你已隐藏的模块，因此存放位置很重要。它有两件事绝不会做：
在任何机器上都不会让你已清除的记录复活，因为删除记录随 Vault 一起迁移；也绝不会覆盖一个已经
有文件的文件夹。

## 参与贡献

欢迎贡献插件、配方、翻译和问题报告，请先阅读 [`CONTRIBUTING.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/CONTRIBUTING.md)。
向插件顾问添加一个插件只需要一个 TOML 文件和两行消息文本。

## 许可证

[Apache-2.0](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/LICENSE)。第三方声明见 [`THIRD_PARTY_NOTICES.md`](https://github.com/ruihaomei/aptuni/blob/v0.2.0b9/THIRD_PARTY_NOTICES.md)。
