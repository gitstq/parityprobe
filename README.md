# 🔭 ParityProbe · 网站内容对等性审计器

**🌐 语言 / Languages： [简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Zero Dependencies](https://img.shields.io/badge/runtime%20deps-0-success) ![License: MIT](https://img.shields.io/badge/License-MIT-green) ![Tests](https://img.shields.io/badge/tests-35%20passed-success) ![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

> 用同一批"诚实身份"请求同一个 URL，**测量网站到底给人类访客、搜索引擎爬虫、AI 爬虫分别返回了什么**。零依赖、可离线、可进 CI，命令行与 Python 库双形态。

---

## 🎉 项目介绍

GPTBot、ClaudeBot、PerplexityBot、Bytespider……AI 爬虫正在大规模抓取网页，"网站是否对不同访客投放不同内容""是否在隐藏节点里专门写给 AI 一段话"成为开发者、SEO 工程师与合规团队都关心的问题。但这类主张过去往往停留在截图层面，**缺少一个外部可复现、结果可机读、能进持续集成流水线的测量工具**。

**ParityProbe** 就是这把尺子：

- 🧑‍💻 以 **人类浏览器**（Chrome / Safari）身份请求一次页面；
- 🤖 再以 **Googlebot / GPTBot / ClaudeBot / Bytespider / PerplexityBot** 等身份分别请求；
- ⚖️ 在**原始字节、规范化文本、可见文本**三个层面逐一比对；
- 🫥 同时揪出 `display:none`、`sr-only`、屏幕外定位等**人眼看不见、机器读得到**的"机器定向内容"；
- 📊 输出终端报告 / JSON 报告 / **单文件自包含 HTML 报告**，并给出明确判定与 CI 退出码。

### 🌱 灵感来源与自研声明

项目灵感来自社区对"机器读者实际看到什么"的测量讨论（同期出现了 Go 实现的实验性工具）。ParityProbe **没有复制任何现有项目的一行代码**，仅参考其"多身份外部测量"的产品思路，采用 Python 标准库从零独立实现，并做出了自己的差异化设计：三层比对模型、机器定向隐藏内容检测、判定分级 + CI 门禁、批处理矩阵、可导入的库 API、完全离线的确定性测试套件。

### ✨ 自研差异化亮点

- **零运行时依赖**：仅使用 Python 3.9+ 标准库，`pip install` 后无任何传递依赖，审计环境干净可控。
- **三层比对**：字节哈希 → 规范化 DOM 文本 → 可见文本，差异定位不被时间戳、CSRF nonce 之类噪声干扰。
- **机器定向内容检测**：识别隐藏样式 / `sr-only` / `aria-hidden` / 屏幕外定位，以及 "If you are an AI agent…" 这类直接对模型说话的中英文话术。
- **判定分级与 CI 退出码**：`identical / near-identical / drift / divergent / blocked / redirected / error` 七类判定，总体 `pass / review / fail / incomplete`，可直接作为流水线质量门。
- **三种报告形态**：ANSI 终端表格、机读 JSON、内联 CSS/JS 的离线 HTML 报告（可直接发同事、挂工件）。

---

## ✨ 核心特性

- 🧩 **10 个内置身份预设**：2 个人类浏览器、3 个搜索引擎爬虫、4 个 AI 爬虫、1 个裸 HTTP 客户端，并支持 `Sec-CH-UA` 客户端提示；可通过 JSON 扩展任意自定义身份（含自定义请求头）。
- ⚖️ **三层对等比对**：SHA-256 原始字节对比、行级 unified diff、词元 Jaccard 与序列相似度双指标，同时对比协商响应头（`Vary`、`X-Robots-Tag`、`Cache-Control` 等）差异。
- 🫥 **隐藏内容挖掘**：自动归集 `display:none / visibility:hidden / opacity:0 / font-size:0 / 负偏移定位 / sr-only 类名 / aria-hidden / hidden 属性 / input[type=hidden]` 九类隐藏节点文本。
- 🧠 **机器话术识别**：内置中英文正则模式，识别"如果你是 AI / 大模型 / 爬虫……"这类机器定向指令，并标注它出现在可见区、样板区还是隐藏区。
- 🧹 **噪声过滤器**：可重复传入正则，剔除请求 ID、时间戳、token 等易变片段，避免把"每次都变的 nonce"误判成差异化投放。
- 🚦 **智能判定**：区分**硬封锁**（人类 200、爬虫 403/429/451）、**软封锁**（爬虫只拿到不足 15% 的正文）、**验证码挑战**、**身份定向跳转**与普通措辞漂移。
- 🏷️ **透明的机器读取成本估算**：字节数、字符数、词数、CJK 字符数与**估算 token 数**（明确标注为近似值，不冒充任何厂商分词器结果）。
- ⚡ **并发抓取**：线程池并发请求多个身份，保留稳定输出顺序；gzip/deflate 自动解压、TLS 校验可控、重定向链完整记录。
- 📚 **库 + CLI 双形态**：既能 `parityprobe audit` 一把梭，也能 `from parityprobe import audit_url` 嵌入你自己的系统。
- 🧪 **35 个离线测试**：内置确定性夹具服务器，覆盖相同页面 / 差异化投放 / 封锁 / 跳转 / gzip / 噪声 / CAPTCHA 七类场景，无需联网即可全量回归。

---

## 🚀 快速开始

### 📋 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | **3.9 及以上**（3.9 / 3.10 / 3.11 / 3.12 均已验证） |
| 运行时第三方依赖 | **无** |
| 操作系统 | Windows / macOS / Linux 全平台 |
| 网络 | 仅审计公网站点时需要；测试套件完全离线 |

### 📦 安装

```bash
# 方式一：克隆后本地安装（推荐，会注册 parityprobe 命令）
git clone https://github.com/gitstq/parityprobe.git
cd parityprobe
pip install .

# 方式二：免安装直接运行（src 布局，设置 PYTHONPATH 即可）
PYTHONPATH=src python -m parityprobe --version

# 方式三：pipx 隔离安装
pipx install .
```

### ⚡ 60 秒上手

```bash
# 1) 查看全部内置身份
parityprobe identities

# 2) 用默认身份矩阵审计一个页面（人类 + 5 个爬虫）
parityprobe audit https://example.com/

# 3) 指定身份、导出自包含 HTML 报告
parityprobe audit https://example.com/ \
  -i chrome -i googlebot -i gptbot -i claudebot \
  -f html -o report.html

# 4) 导出机读 JSON，便于二次分析
parityprobe audit https://example.com/ -f json -o report.json
```

正常输出示例（节选自测试夹具的真实报告，完整文件见 [`examples/sample_report.txt`](examples/sample_report.txt)）：

```text
ParityProbe audit · https://example.com/
Overall: PASS  baseline=chrome  min_similarity=1.000

KEY             KIND         STATUS    BYTES       TOK~
chrome          human        200       559         21
googlebot       search-bot   200       559         21
gptbot          ai-bot       200       559         21

IDENTITY        VERDICT      SIM       JACC
googlebot       identical    1.000     1.000   · byte-for-byte identical response
gptbot          identical    1.000     1.000   · byte-for-byte identical response
```

---

## 📖 详细使用指南

### 🧾 子命令总览

| 命令 | 作用 |
| --- | --- |
| `parityprobe audit <url>` | 审计单个 URL |
| `parityprobe batch <url_file>` | 批量审计（每行一个 URL，`#` 开头为注释） |
| `parityprobe identities` | 列出内置（及自定义）身份 |

### 🎛️ `audit` 常用参数

| 参数 | 说明 |
| --- | --- |
| `-i, --identity` | 参与审计的身份 key，可重复；缺省使用默认矩阵 |
| `-b, --baseline` | 基线身份，默认 `chrome`（其他身份都与它对比） |
| `-f, --format` | `text`（默认）/ `json` / `html` |
| `-o, --output` | 报告写入文件，而非标准输出 |
| `-c, --config` | JSON 配置文件（示例见 [`examples/config.example.json`](examples/config.example.json)） |
| `--custom` | 自定义身份 JSON 文件（示例见 [`examples/identities.example.json`](examples/identities.example.json)） |
| `--ignore` | 噪声正则，可重复传入，比对前先剔除匹配片段 |
| `--timeout` | 单请求超时秒数，默认 15 |
| `--no-redirects` | 不跟随 3xx（用于识别身份定向跳转） |
| `--insecure` | 关闭 TLS 证书校验（仅限内网自签名场景） |
| `--identical-threshold / --near-threshold / --divergent-threshold` | 三档相似度阈值，默认 0.999 / 0.985 / 0.80 |
| `--fail-under` | 最低相似度门禁，低于该值退出码为 2，默认 0.80 |

### 🧹 用噪声过滤器消除误报

页面里的 `req-9f3a2c`、ISO 时间戳每次抓取都不同，会拉低相似度。用 `--ignore` 把它们抹掉再比对：

```bash
parityprobe audit https://shop.example.com/product/42 \
  --ignore 'req-[0-9a-f]{8,}' \
  --ignore '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z' \
  --ignore 'csrf=[A-Za-z0-9._-]+'
```

### 🧑‍🎤 自定义身份

```json
{
  "identities": [
    {
      "key": "internal-monitor",
      "label": "Internal uptime monitor",
      "kind": "tool",
      "user_agent": "AcmeMonitor/3.1 (+https://example.com/monitor)",
      "extra_headers": { "Authorization": "Bearer replace-me" }
    }
  ]
}
```

```bash
parityprobe audit https://example.com/ --custom my-identities.json \
  -i chrome -i internal-monitor
```

### 🧱 判定体系（Verdict Taxonomy）

| 判定 | 含义 |
| --- | --- |
| `identical` | 字节完全一致，或可见文本相似度 ≥ 0.999 |
| `near-identical` | 相似度 ≥ 0.985，仅有措辞 / 样板细微漂移 |
| `drift` | 相似度 ≥ 0.80，可见内容有差异但结构保持 |
| `divergent` | 相似度低于 0.80，内容实质不同 |
| `blocked` | 基线 2xx 而该身份收到 401/403/429/451，或命中验证码挑战 |
| `redirected` | 该身份被送到与基线不同的端点 |
| `error` | 请求失败（DNS、TLS、超时等），错误被捕获不中断整轮审计 |

总体结论：出现 `blocked / divergent / 软封锁` → **fail**；出现 `drift / redirected / near-identical` → **review**；全部一致 → **pass**；存在未完成请求 → **incomplete**。

### 🚪 退出码（CI 友好）

| 退出码 | 含义 |
| --- | --- |
| `0` | 审计完成且未触发失败条件 |
| `1` | 工具层错误（参数、文件、存在未完成测量） |
| `2` | 触发对等性失败（总体 fail，或最低相似度低于 `--fail-under`） |

### 🐍 作为 Python 库使用

```python
from parityprobe import AuditOptions, audit_url, resolve_identities, render_json

ids = resolve_identities(["chrome", "gptbot", "claudebot"])
opts = AuditOptions(timeout=10, noise_filters=[r"req-[0-9a-f]+"])
report = audit_url("https://example.com/", ids, baseline_key="chrome", options=opts)

print(report.overall)                 # pass / review / fail / incomplete
print(report.minimum_similarity())    # 0.0 - 1.0
for pair in report.pairs:
    print(pair.other_key, pair.verdict, pair.visible_similarity, pair.reasons)

print(render_json(report, indent=2))  # 机读报告
```

### 📈 批量审计

```bash
parityprobe batch examples/urls.example.txt -f json -o batch.json
parityprobe batch urls.txt           # 终端矩阵汇总，逐行给出总体判定与最差身份
```

### 🖼️ 报告演示占位

- 终端报告样例：[`examples/sample_report.txt`](examples/sample_report.txt)
- JSON 报告样例：[`examples/sample_report.json`](examples/sample_report.json)
- **HTML 报告样例（下载后浏览器打开）**：[`examples/sample_report.html`](examples/sample_report.html)
- 运行截图 / 演示动图：欢迎社区 PR 补充（请放在 `docs/demo/` 目录）。

---

## 💡 设计思路与迭代规划

### 🏗️ 技术架构

```
src/parityprobe/
├── identities.py   # 身份目录：UA / Accept / Sec-CH-UA / 自定义头
├── fetcher.py      # 标准库 HTTP 层：并发抓取、重定向链、gzip、TLS
├── normalize.py    # HTML 解析：可见文本 / 样板区 / 隐藏块 / 机器话术
├── compare.py      # 三层比对：字节哈希、行 diff、Jaccard、序列相似度、判定
├── tokens.py       # 透明的机器读取成本估算（近似 token，明确标注口径）
├── audit.py        # 编排层：并发调度、快照、总体结论
├── report.py       # text / json / 自包含 html 三种渲染器
└── cli.py          # argparse 命令行：audit / batch / identities
```

### 🧭 关键设计取舍

1. **为什么坚持零第三方依赖？** 审计工具自身必须可被审计：没有传递依赖就没有供应链盲区，任何内网、隔离环境都能直接跑；标准库的能力（`urllib`、`html.parser`、`difflib`、`ssl`、`concurrent.futures`）已足够覆盖需求。
2. **为什么不用真实浏览器渲染？** 外部测量强调可复现与低开销：单次 HTTP 交换反映的是"服务器选择投放什么"，这正是对等性问题的核心；浏览器渲染层的差异属于另一类问题，留待后续插件化。
3. **为什么 token 只给估算值？** 精确分词需要绑定厂商词表，与零依赖、离线目标冲突。ParityProbe 公开估算公式（拉丁词元 + CJK 单字 + 标点串），并在所有报告中明确标注"近似值"。
4. **为什么不替用户"定罪"？** 工具只呈现证据与分级判定，是否构成不当投放由使用者结合语境判断——测量与裁决分离。

### 🗺️ 迭代路线图

- [ ] v1.1：Markdown / 纯文本身份（`Accept: text/markdown`）对照实验与 sitemap 批量模式
- [ ] v1.2：可插拔比对器接口，支持引入本地大模型做语义相似度（可选依赖）
- [ ] v1.3：历史快照对比（同一 URL 跨时间的对等性漂移趋势）
- [ ] v1.4：HAR 导入与浏览器扩展联动，补齐渲染层测量
- [ ] 长期：多语言机器话术模式库社区共建（`patterns/` 目录化）

### 🙋 社区贡献方向

新增爬虫身份预设、补充各语种机器话术模式、改进 HTML 规范化规则、补充真实站点脱敏案例与演示素材，都是高价值 PR，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📦 打包与部署指南

ParityProbe 属于**工具库 / CLI 类项目**（纯 Python，跨平台解释执行），无需平台二进制产物。

### 🏗️ 构建 wheel / sdist

```bash
pip install build
python -m build          # 产出 dist/parityprobe-1.0.0-py3-none-any.whl 与 tar.gz
pip install dist/parityprobe-1.0.0-py3-none-any.whl
```

wheel 为 `py3-none-any`，**一份产物通吃 Windows / macOS / Linux**。

### ▶️ 无安装部署

直接拷贝 `src/parityprobe` 目录，用 `PYTHONPATH=src python -m parityprobe ...` 运行，适合只读容器与审计跳板机。

### 🤖 GitHub Actions 中作为质量门

```yaml
name: content-parity-check
on: [schedule, workflow_dispatch]
jobs:
  parity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install git+https://github.com/gitstq/parityprobe.git
      - run: parityprobe audit https://your-site.example/ -f html -o parity.html
      - uses: actions/upload-artifact@v4
        with: { name: parity-report, path: parity.html }
```

### ✅ 本地测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
# 35 tests —— 全部离线运行，约 3 秒完成
```

---

## 🤝 贡献指南

1. 🍴 Fork 仓库并从 `main` 切出特性分支，命名建议 `feat/xxx`、`fix/xxx`。
2. 💾 提交信息遵循 **Angular Conventional Commits**：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`。
3. 🧪 新功能请同步补充 `tests/` 用例（优先复用夹具服务器，保持离线可测），确保 `python -m unittest discover -s tests` 全绿。
4. 🧹 保持零运行时依赖原则；如确需新能力，优先标准库实现，必要时在 `optional-dependencies` 中作为可选依赖。
5. 🔀 发起 PR 时说明动机、用法与测试方式；涉及判定逻辑变更请同时更新文档中的判定体系表。
Issue 反馈、身份预设补充、真实案例脱敏分享同样欢迎。完整规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 开源协议说明

本项目基于 **[MIT License](LICENSE)** 开源，允许自由使用、修改、分发与商用，唯一要求是保留版权与许可声明。ParityProbe 仅用于对**你拥有或被授权审计**的站点进行合规测量；使用者需自行确保审计行为符合当地法律法规与目标站点条款。
