# 🔭 ParityProbe · 網站內容對等性稽核器

**🌐 語言： [简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Zero Dependencies](https://img.shields.io/badge/runtime%20deps-0-success) ![License: MIT](https://img.shields.io/badge/License-MIT-green) ![Tests](https://img.shields.io/badge/tests-35%20passed-success) ![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

> 用同一批「誠實身分」請求同一個網址，**實測網站到底分別給人類訪客、搜尋引擎爬蟲、AI 爬蟲送了什麼內容**。零相依、可離線、能接 CI，同時提供命令列與 Python 函式庫兩種型態。

---

## 🎉 專案介紹

GPTBot、ClaudeBot、PerplexityBot、Bytespider……AI 爬蟲正大規模擷取整個網路，「網站是否對不同訪客投放不同內容」「是否在隱藏節點裡，特別寫了一段話給 AI 看」成了開發者、SEO 工程師與法務合規團隊共同關心的議題。但這類主張過去往往只停留在截圖層次，**欠缺一個外部可重現、結果可機讀、能放進持續整合管線的量測工具**。

**ParityProbe** 就是這把尺：

- 🧑‍💻 先以**人類瀏覽器**（Chrome / Safari）身分請求一次頁面；
- 🤖 再分別以 **Googlebot / GPTBot / ClaudeBot / Bytespider / PerplexityBot** 等身分各請求一次；
- ⚖️ 在**原始位元組、正規化文字、可見文字**三個層級逐一比對；
- 🫥 同時揪出 `display:none`、`sr-only`、螢幕外定位這種「人眼看不見、機器讀得到」的**機器導向內容**；
- 📊 輸出終端機報告 / JSON 報告 / **單檔自包含 HTML 報告**，並給出明確判定與 CI 結束碼。

### 🌱 靈感來源與自研聲明

專案靈感來自社群對於「機器讀者實際看到什麼」的量測討論（同期亦出現過實驗性的 Go 實作）。ParityProbe **未複製任何現有專案的半行程式碼**，只保留「以多種身分從外部量測」這個產品發想，全數以 Python 標準函式庫從零獨立實作，並發展出自己的差異化設計：三層比對模型、機器導向隱藏內容偵測、判定分級加上 CI 品質管門、批次稽核矩陣、可匯入的函式庫 API，以及完全離線、具確定性的測試套件。

### ✨ 自研差異化亮點

- **零執行階段相依**：只使用 Python 3.9+ 標準函式庫，安裝後沒有任何傳遞相依，稽核環境乾淨、可控、可被檢視。
- **三層比對**：位元組雜湊 → 正規化 DOM 文字 → 可見文字，不讓時間戳、CSRF nonce 這類雜訊干擾差異判定。
- **機器導向內容偵測**：辨識隱藏樣式、`sr-only`、`aria-hidden`、螢幕外定位，以及「If you are an AI agent…」「如果你是 AI／大模型／爬蟲……」這類直接對模型說話的中英文話術。
- **判定分級與 CI 結束碼**：`identical / near-identical / drift / divergent / blocked / redirected / error` 七類判定，總結為 `pass / review / fail / incomplete`，可直接作為管線品質門。
- **三種報告型態**：ANSI 終端表格、機讀 JSON、內嵌 CSS/JS 的離線 HTML 報告，方便轉發與作為建置產物留存。

---

## ✨ 核心特性

- 🧩 **內建 10 組身分預設**：2 組人類瀏覽器、3 組搜尋引擎爬蟲、4 組 AI 爬蟲、1 組裸 HTTP 用戶端，並支援 `Sec-CH-UA` 用戶端提示；可透過 JSON 擴充任意自訂身分（含自訂請求標頭）。
- ⚖️ **三層對等比對**：SHA-256 原始位元組比對、行級 unified diff、詞元 Jaccard 與序列相似度雙指標，同時比對協商回應標頭（`Vary`、`X-Robots-Tag`、`Cache-Control` 等）差異。
- 🫥 **隱藏內容挖掘**：自動收集 `display:none / visibility:hidden / opacity:0 / font-size:0 / 負偏移定位 / sr-only 類別 / aria-hidden / hidden 屬性 / input[type=hidden]` 共九類隱藏節點的文字。
- 🧠 **機器話術辨識**：內建中英文規則樣式，辨識直接對 AI、大模型、爬蟲下指令的語句，並標註它出現在可見區、版權列樣板區還是隱藏區。
- 🧹 **雜訊過濾器**：可重複帶入正規表示式，剔除請求識別碼、時間戳、權杖等易變片段，避免把「每次都變的 nonce」誤判為差別投放。
- 🚦 **智慧判定**：區分**硬封鎖**（人類 200、爬蟲 403/429/451）、**軟封鎖**（爬蟲只拿到不到 15% 正文）、**驗證碼挑戰**、**身分型導向跳轉**與一般用語漂移。
- 🏷️ **透明的機器讀取成本估算**：位元組數、字元數、詞數、CJK 字元數與**估算 token 數**（清楚標註為近似值，不冒充任何廠商分詞器的結果）。
- ⚡ **並發抓取**：以執行緒集區並發請求多個身分，輸出順序保持穩定；gzip/deflate 自動解壓縮、TLS 驗證可調、重新導向鏈完整記錄。
- 📚 **函式庫＋命令列雙型態**：既能 `parityprobe audit` 一鍵完成，也能 `from parityprobe import audit_url` 嵌入自有系統。
- 🧪 **35 個離線測試**：內建具確定性的測試夾具伺服器，涵蓋相同頁面／差別投放／封鎖／跳轉／gzip／雜訊／CAPTCHA 七種場景，不需聯網即可完整回歸。

---

## 🚀 快速開始

### 📋 環境需求

| 項目 | 需求 |
| --- | --- |
| Python | **3.9 以上**（3.9 / 3.10 / 3.11 / 3.12 皆已驗證） |
| 第三方執行相依 | **無** |
| 作業系統 | Windows / macOS / Linux 全平台 |
| 網路 | 僅稽核公開網站時需要；測試套件完全離線 |

### 📦 安裝

```bash
# 方式一：克隆後本機安裝（推薦，會註冊 parityprobe 指令）
git clone https://github.com/gitstq/parityprobe.git
cd parityprobe
pip install .

# 方式二：免安裝直接執行（src 佈局，設定 PYTHONPATH 即可）
PYTHONPATH=src python -m parityprobe --version

# 方式三：以 pipx 隔離安裝
pipx install .
```

### ⚡ 60 秒上手

```bash
# 1) 查看全部內建身分
parityprobe identities

# 2) 以預設身分矩陣稽核單一頁面（人類 + 5 個爬蟲）
parityprobe audit https://example.com/

# 3) 指定身分，並匯出自包含 HTML 報告
parityprobe audit https://example.com/ \
  -i chrome -i googlebot -i gptbot -i claudebot \
  -f html -o report.html

# 4) 匯出機讀 JSON，方便後續分析
parityprobe audit https://example.com/ -f json -o report.json
```

正常輸出範例（節錄自測試夾具的真實報告，完整內容見 [`examples/sample_report.txt`](examples/sample_report.txt)）：

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

## 📖 詳細使用指南

### 🧾 子指令一覽

| 指令 | 用途 |
| --- | --- |
| `parityprobe audit <url>` | 稽核單一網址 |
| `parityprobe batch <url_file>` | 批次稽核（每行一個網址，`#` 開頭為註解） |
| `parityprobe identities` | 列出內建（與自訂）身分 |

### 🎛️ `audit` 常用參數

| 參數 | 說明 |
| --- | --- |
| `-i, --identity` | 參與稽核的身分 key，可重複帶入；預設使用內建矩陣 |
| `-b, --baseline` | 基線身分，預設 `chrome`（其他身分都與它比對） |
| `-f, --format` | `text`（預設）/ `json` / `html` |
| `-o, --output` | 將報告寫入檔案，而非標準輸出 |
| `-c, --config` | JSON 設定檔（範例見 [`examples/config.example.json`](examples/config.example.json)） |
| `--custom` | 自訂身分 JSON 檔（範例見 [`examples/identities.example.json`](examples/identities.example.json)） |
| `--ignore` | 雜訊正規表示式，可重複帶入，比對前先剔除匹配片段 |
| `--timeout` | 單一請求逾時秒數，預設 15 |
| `--no-redirects` | 不跟隨 3xx 重新導向（用於辨識身分型導向跳轉） |
| `--insecure` | 關閉 TLS 憑證驗證（僅限內網自簽憑證情境） |
| `--identical-threshold / --near-threshold / --divergent-threshold` | 三檔相似度門檻，預設 0.999 / 0.985 / 0.80 |
| `--fail-under` | 最低相似度管門，低於此值結束碼為 2，預設 0.80 |

### 🧹 用雜訊過濾消除誤判

頁面中的 `req-9f3a2c`、ISO 時間戳每次抓取都不同，會拉低相似度。用 `--ignore` 先移除再比對：

```bash
parityprobe audit https://shop.example.com/product/42 \
  --ignore 'req-[0-9a-f]{8,}' \
  --ignore '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z' \
  --ignore 'csrf=[A-Za-z0-9._-]+'
```

### 🧑‍🎤 自訂身分

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

### 🧱 判定體系（Verdict Taxonomy）

| 判定 | 涵義 |
| --- | --- |
| `identical` | 位元組完全相同，或可見文字相似度 ≥ 0.999 |
| `near-identical` | 相似度 ≥ 0.985，僅有用語／樣板細微漂移 |
| `drift` | 相似度 ≥ 0.80，可見內容有差異但整體結構仍在 |
| `divergent` | 相似度低於 0.80，內容實質不同 |
| `blocked` | 基線得到 2xx，該身分卻收到 401/403/429/451，或命中驗證碼挑戰 |
| `redirected` | 該身分被送到與基線不同的端點 |
| `error` | 請求失敗（DNS、TLS、逾時等），錯誤會被捕捉，不會中斷整輪稽核 |

總體結論：出現 `blocked / divergent / 軟封鎖` → **fail**；出現 `drift / redirected / near-identical` → **review**；全部一致 → **pass**；存在未完成的請求 → **incomplete**。

### 🚪 結束碼（CI 友善）

| 結束碼 | 涵義 |
| --- | --- |
| `0` | 稽核完成且未觸發失敗條件 |
| `1` | 工具層錯誤（參數、檔案、存在未完成的量測） |
| `2` | 觸發對等性失敗（總體 fail，或最低相似度低於 `--fail-under`） |

### 🐍 作為 Python 函式庫使用

```python
from parityprobe import AuditOptions, audit_url, resolve_identities, render_json

ids = resolve_identities(["chrome", "gptbot", "claudebot"])
opts = AuditOptions(timeout=10, noise_filters=[r"req-[0-9a-f]+"])
report = audit_url("https://example.com/", ids, baseline_key="chrome", options=opts)

print(report.overall)              # pass / review / fail / incomplete
print(report.minimum_similarity()) # 0.0 - 1.0
for pair in report.pairs:
    print(pair.other_key, pair.verdict, pair.visible_similarity, pair.reasons)

print(render_json(report, indent=2))  # 機讀報告
```

### 📈 批次稽核

```bash
parityprobe batch examples/urls.example.txt -f json -o batch.json
parityprobe batch urls.txt       # 終端矩陣摘要，逐列列出總判定與最差身分
```

### 🖼️ 報告展示位置

- 終端報告範例：[`examples/sample_report.txt`](examples/sample_report.txt)
- JSON 報告範例：[`examples/sample_report.json`](examples/sample_report.json)
- **HTML 報告範例（下載後以瀏覽器開啟）**：[`examples/sample_report.html`](examples/sample_report.html)
- 操作截圖／展示短片：歡迎社群 PR 補充（請置於 `docs/demo/` 目錄）。

---

## 💡 設計思路與迭代規劃

### 🏗️ 技術架構

```
src/parityprobe/
├── identities.py   # 身分目錄：UA / Accept / Sec-CH-UA / 自訂標頭
├── fetcher.py      # 標準函式庫 HTTP 層：並發抓取、重新導向鏈、gzip、TLS
├── normalize.py    # HTML 解析：可見文字 / 樣板區 / 隱藏塊 / 機器話術
├── compare.py      # 三層比對：位元組雜湊、行 diff、Jaccard、序列相似度、判定
├── tokens.py       # 透明的機器讀取成本估算（近似 token，清楚標註口徑）
├── audit.py        # 編排層：並發排程、快照、總體結論
├── report.py       # text / json / 自包含 html 三種渲染器
└── cli.py          # argparse 命令列：audit / batch / identities
```

### 🧭 關鍵設計取捨

1. **為什麼堅持零第三方相依？** 稽核工具本身必須可被檢視：沒有傳遞相依就沒有供應鏈盲區，任何內網、隔離環境都能直接執行；而標準函式庫（`urllib`、`html.parser`、`difflib`、`ssl`、`concurrent.futures`）已足以覆蓋全部需求。
2. **為什麼不用真實瀏覽器渲染？** 外部量測強調可重現與低負荷：單次 HTTP 交換反映的是「伺服器選擇投放什麼」，這正是對等性問題的核心；渲染層差異屬於另一類問題，留待後續以外掛方式補上。
3. **為什麼 token 只給估算值？** 精確分詞需要綁定廠商詞表，與零相依、可離線的目標衝突。ParityProbe 公開估算公式（拉丁詞元＋CJK 單字＋標點串），並在所有報告中清楚標註為近似值。
4. **為什麼不直接替使用者定罪？** 工具只呈現證據與分級判定，差別投放是否不當，留給使用者依情境判斷——量測與裁決分離。

### 🗺️ 迭代路線圖

- [ ] v1.1：Markdown／純文字身分（`Accept: text/markdown`）對照實驗，以及 sitemap 批次模式
- [ ] v1.2：可插拔比對器介面，支援引入本機模型做語意相似度（選用相依）
- [ ] v1.3：歷史快照比對（同一網址跨時間的對等性漂移趨勢）
- [ ] v1.4：HAR 匯入與瀏覽器擴充功能聯動，補齊渲染層量測
- [ ] 長期：多語言機器話術樣式庫由社群共編（`patterns/` 目錄化）

### 🙋 社群貢獻方向

新增爬蟲身分預設、補充各語言機器話術樣式、改進 HTML 正規化規則、提供去識別化的真實案例與展示素材，都是高價值 PR，詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📦 打包與部署指南

ParityProbe 屬於**工具庫／命令列**類型的專案（純 Python、直譯執行、跨平台），不需要各平台的二進位產物。

### 🏗️ 建構 wheel / sdist

```bash
pip install build
python -m build          # 產出 dist/parityprobe-1.0.0-py3-none-any.whl 與 .tar.gz
pip install dist/parityprobe-1.0.0-py3-none-any.whl
```

wheel 標記為 `py3-none-any`，**一份產物通用 Windows / macOS / Linux**。

### ▶️ 無安裝部署

直接複製 `src/parityprobe` 目錄，以 `PYTHONPATH=src python -m parityprobe ...` 執行，適合唯讀容器與稽核跳板機。

### 🤖 在 GitHub Actions 作為品質門

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

### ✅ 本機測試

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
# 35 個測試 —— 全程離線，約 3 秒完成
```

---

## 🤝 貢獻指南

1. 🍴 Fork 專案並從 `main` 切出特性分支，建議命名 `feat/xxx`、`fix/xxx`。
2. 💾 提交訊息遵循 **Angular Conventional Commits**：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`。
3. 🧪 新功能請同步補上 `tests/` 測試（優先複用測試夾具伺服器，維持離線可測），確保 `python -m unittest discover -s tests` 全綠。
4. 🧹 維持零執行相依原則；若確有需要，優先以標準函式庫實作，必要時才放進 `optional-dependencies` 作為選用相依。
5. 🔀 提交 PR 時請說明動機、用法與測試方式；若變更判定邏輯，請同步更新文件中的判定體系表格。

Issue 回報、身分預設補充、去識別化真實案例分享同樣歡迎。完整規範見 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 開源授權說明

本專案以 **[MIT License](LICENSE)** 授權開源，允許自由使用、修改、散布與商用，唯一要求是保留著作權與授權聲明。ParityProbe 僅適用於對**你擁有或已獲授權稽核**的網站進行合規量測；使用者須自行確保稽核行為符合當地法規與目標網站條款。
