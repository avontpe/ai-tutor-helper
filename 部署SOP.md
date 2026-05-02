# 🚀 v3.5 部署接續 SOP（從中斷點繼續）

> 您先前的進度：已上傳檔案到 GitHub、已取得 Gemini Key、卡在 Streamlit 部署的權限問題。
> 現在的方向：改倉庫名稱 + 程式碼通用化（v3.5）
> 預估剩餘時間：30-45 分鐘

---

## 📋 您現在要做的 5 件事

```
1. 改倉庫名稱（queenie-app → ai-tutor-helper）  3 分鐘
2. 把 GitHub 上的舊檔案全刪掉                   2 分鐘
3. 上傳 v3.5 新檔案                            5 分鐘
4. 改倉庫為 Public                             1 分鐘
5. Streamlit 部署 + 設定 Secrets               10 分鐘
```

---

# Step 1：改倉庫名稱

## 動作 1-1：開啟 GitHub 倉庫設定
👉 https://github.com/avontpe/queenie-app/settings

## 動作 1-2：找到頂部 "Repository name" 欄位

```
┌──────────────────────────────────────┐
│  General                             │
│                                      │
│  Repository name *                   │
│  ┌──────────────────────────────┐   │
│  │ queenie-app                   │   │ ← 這裡改
│  └──────────────────────────────┘   │
│  [ Rename ]                          │
└──────────────────────────────────────┘
```

## 動作 1-3：把 `queenie-app` 改成：

```
ai-tutor-helper
```

點 **Rename** 按鈕。

## ✅ 完成
GitHub 會顯示確認訊息，倉庫網址自動更新為：
```
https://github.com/avontpe/ai-tutor-helper
```

---

# Step 2：刪除 GitHub 上的舊檔案

⚠️ **為什麼要刪？** 因為 v3.5 程式碼變了，要全部換新。

## 方法 A：逐個刪除（適合 5 個檔案）

進入新網址：
👉 https://github.com/avontpe/ai-tutor-helper

對**每個檔案**（除了 `cat_photos/` 資料夾）：
1. 點檔案進入
2. 右上角找到 **垃圾桶圖示 🗑️** 或 **More options → Delete file**
3. 點「Delete file」 → 滑到底點 **Commit changes**

要刪的檔案：
- ✅ `queenie_app.py`
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `配置SOP.md`（中文檔名那個）

⚠️ **不要刪** `cat_photos/` 資料夾（裡面的小吉照片要保留！）

## 方法 B：直接重建倉庫（更乾淨，但要重傳照片）

如果方法 A 太麻煩，就：
1. 把整個倉庫刪掉
2. 重建一個叫 `ai-tutor-helper` 的空倉庫
3. 重新上傳所有 v3.5 檔案（含 cat_photos/）

---

# Step 3：上傳 v3.5 新檔案

## 動作 3-1：在倉庫首頁點 "Add file → Upload files"

## 動作 3-2：拖曳以下檔案進去（**進入 v3.5 資料夾後全選 5 個項目**）

```
v3.5 資料夾內容：
├── queenie_app.py        ← v3.5 通用化版本
├── requirements.txt
├── README.md
├── SECRETS_範本.txt      ← ⚠️ 不要傳這個！這是給您看的
└── cat_photos/           ← 如果方法 B 才需要傳
    ├── 小吉_01.jpg
    └── 小吉_走來囉.mp4
```

⚠️ **千萬不要把 `SECRETS_範本.txt` 上傳到 GitHub**！它有您的學校資訊。

## 動作 3-3：點綠色 "Commit changes" 上傳

---

# Step 4：把倉庫改為 Public

⚠️ **為什麼要改 Public？**
因為 Streamlit Cloud 免費版**只能讀 Public 倉庫**。
v3.5 已經把所有個人資訊抽離，改 Public 完全安全 ✅

## 動作 4-1：進入倉庫設定
👉 https://github.com/avontpe/ai-tutor-helper/settings

## 動作 4-2：滑到底部 Danger Zone → Change visibility → Make public

照之前的流程：
1. 確認 → 輸入 `avontpe/ai-tutor-helper` → 點紅色按鈕

## ✅ 完成
右上角從 🔒 Private 變成 🌐 Public

---

# Step 5：Streamlit Cloud 部署

## 動作 5-1：開啟 Streamlit Cloud
👉 https://share.streamlit.io

## 動作 5-2：登入後點右上「創建應用」

## 動作 5-3：選 "Deploy a public app from GitHub"

## 動作 5-4：填表單

| 欄位 | 填寫內容 |
|------|---------|
| Repository | `avontpe/ai-tutor-helper` ⭐ 新名字 |
| Branch | `main` |
| Main file path | `queenie_app.py` |
| App URL | 自訂（建議 `study-app-2027` 或 `ai-tutor`）|

⚠️ App URL **不要包含** queenie 或女兒名字！

## 動作 5-5：⚠️ **點 "Advanced settings"！**

## 動作 5-6：在 Secrets 欄位**完整貼上**以下內容

開啟您下載的 `SECRETS_範本.txt`，**完整複製整個檔案內容**，貼到 Streamlit 的 Secrets 欄位。

然後**修改這幾個地方**：

1. `GOOGLE_API_KEY = "AIza_把您的Gemini_Key貼這裡"`
   → 改成您真正的 Gemini Key（從記事本貼過來）

2. 其他資料**已經填好**：
   - STUDENT_NAME = "Queenie"
   - SCHOOL_NAME = "中信高中"
   - EXAM_YEAR = "116"
   - EXAM_DATE = "2027-01-22"
   - DEFAULT_GRADE = "高二"
   - CAT_NAME = "小吉"
   - TEXTBOOK_JSON = '{...龍騰、泰宇、南一對應...}'

## 動作 5-7：點藍色 "Deploy!" 按鈕

## ⏳ 等 3-5 分鐘部署完成

---

# 🎯 部署成功的訊號

看到這個畫面 = **完美成功！** 🎉

```
┌───────────────────────────────────────────┐
│ 🐱 [小吉照片]                              │
│    😿 小吉                                 │
│    "主人～今天還沒開始念書喔，小吉在等你！"│
│                                           │
│ 🎓 Hi Q~ 學測導航                          │
│ 🤖 AI 引擎: [Gemini ●] [Claude]           │
│                                           │
│ 📚 中信高中 龍騰版 高二國文                │
│ ─────────────────────────                  │
│  距離 116 學測  Phase 1     每日目標       │
│  265 天        🌱 補洞期    15 題          │
└───────────────────────────────────────────┘
```

對 Queenie 而言：個人化（看到「中信高中」、「Hi Q~」）
對外人而言：通用化（程式碼裡只有「同學」、「通用版」）

---

# 🆘 遇到問題

任何時候卡住 → **截圖給我**，我立刻幫您診斷！

---

# 🎓 給您的最後叮嚀

## v3.5 的隱私保護機制

| 項目 | 公開（GitHub）| 私密（Streamlit Secrets）|
|------|--------------|----------------------|
| 程式碼邏輯 | ✅ 公開 | - |
| 學生名字「Queenie」| ❌ | ✅ 在 Secrets |
| 學校「中信高中」| ❌ | ✅ 在 Secrets |
| 教科書版本 | ❌ | ✅ 在 Secrets |
| 學測年度 116 | ❌ | ✅ 在 Secrets |
| 小吉的個性描述 | ❌ | ✅ 在 Secrets |
| 小吉的照片 | ✅ 公開 | - |
| Queenie 的學習紀錄 | ❌ | ✅ Streamlit DB |
| API Keys | ❌ | ✅ 在 Secrets |

✅ **完美的「資訊分層」**：對外通用、對內個人化
