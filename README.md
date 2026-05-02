# 🎓 AI Tutor Helper v3.5

跨裝置雲端網頁 App + AI 雙引擎 + 學習進度追蹤 + 寵物夥伴系統

## ✨ 核心功能

- 🤖 **雙 AI 引擎切換**（Claude / Gemini）
- 📅 **每日任務面板**
- 📝 **段考刷題 + 蘇格拉底引導**
- 🔁 **智慧錯題本**（SQLite 持久化）
- 📊 **分數趨勢追蹤**
- 🎯 **學測倒數 + 階段進度**
- 📱 **PWA 支援**（可加入 iPad 主畫面）
- 🐱 **寵物夥伴互動**（提升使用黏著度）
- 💰 **API 費用即時監控**
- 🔒 **個資分離設計**（個人資訊存於 Secrets，程式碼通用化）

## 🚀 快速部署

### 1. Fork 或下載本倉庫

### 2. 部署到 Streamlit Cloud

| 欄位 | 內容 |
|------|------|
| Repository | `your-account/ai-tutor-helper` |
| Branch | `main` |
| Main file path | `queenie_app.py` |

### 3. 設定 Secrets（Settings → Secrets）

```toml
# AI Engines
GOOGLE_API_KEY = "AIza..."
ANTHROPIC_API_KEY = "sk-ant-..."  # 選填
MONTHLY_BUDGET_USD = "20"

# 個人化設定
STUDENT_NAME = "同學暱稱"
SCHOOL_NAME = "你的學校"
EXAM_YEAR = "116"
EXAM_DATE = "2027-01-22"
DEFAULT_GRADE = "高二"

# 寵物夥伴
CAT_NAME = "小貓"
CAT_PERSONALITY = "可愛的貓咪"

# 教科書版本（JSON 格式）
TEXTBOOK_JSON = '{"國文":{"高二":"龍騰","高三":"龍騰"}, ...}'
```

### 4. 取得 API Keys

- **Gemini**：https://aistudio.google.com/app/apikey （免費）
- **Claude**：https://console.anthropic.com/settings/keys （需儲值）

## 🐱 寵物夥伴功能

把寵物照片或影片放到 `cat_photos/` 資料夾，App 會自動讀取並隨機輪播。

### 支援格式
- 📸 照片：jpg、jpeg、png、webp、gif
- 🎬 影片：mp4、webm、mov（自動播放、循環、靜音）

### 互動規則
寵物會依今日完成度顯示不同表情和鼓勵語：
- 0%：😿 「今天還沒開始念書喔！」
- 1-49%：😺 「再 push 一下！」
- 50-99%：🐱 「快達標了！」
- 100%+：😻 「今天好棒！」

連續達標會顯示 🔥 連續 X 天 徽章。

## 🎯 學測階段時間軸

| Phase | 時間 | 重點 | 每日目標 |
|-------|------|------|---------|
| 🌱 補洞期 | 5-6 月 | 跟段考 + 補弱點 | 15 題 |
| 🔥 暑假黃金期 | 7-9 月 | 全範圍重新梳理 | 35 題 |
| ⚡ 模考衝刺 | 10-12 月 | 歷屆學測 + 計時 | 50 題 |
| 🎯 考前精修 | 1 月 | 只回顧錯題本 | 20 題 |

## 💰 預估費用

| 強度 | 月費（USD）| 月費（NT$）|
|------|----------|----------|
| 輕度 | $3-8 | $100-250 |
| 中度（建議）| $8-15 | $250-500 |

## 📱 加入 iPad 主畫面

1. iPad 用 Safari 打開 App 網址
2. 點分享 → **加入主畫面**
3. 全螢幕 App 體驗

## 🔧 技術架構

- **前端框架**：Streamlit
- **AI 引擎**：Anthropic Claude + Google Gemini
- **資料庫**：SQLite（本地持久化）
- **部署**：Streamlit Community Cloud
- **隱私模型**：程式碼公開、個資存於 Secrets

## 📜 授權

個人使用、教育用途。
