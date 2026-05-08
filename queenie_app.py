"""
AI Tutor Helper v3.7.1（首頁優化版）
================================
跨裝置雲端網頁 App（iPad / 桌機 / 手機皆可用）

v3.7 重大改造（2026-05-08）：
- 🎯 真考試模式：作答按鈕（A/B/C/D）→ 計時 → 一鍵交卷 → 自動評分
- 📌 一鍵加錯題本（不用打字）
- 🎨 D 儀表板風 UI（深藏青 + 白底 + 細邊框）
- 📋 簡潔階段命名：基礎期 / 衝刺期 / 模擬期 / 決勝期
- ⚡ 修復 Gemini 2.5-flash + 多模型 fallback

v3.6 基礎功能：
- 🔐 雙層密碼保護（學生 + 家長後台）
- 💰 統一 NT$ 顯示 + 自然月計費
- 📚 數學雙軌制（學校 B + 學測 A）
- 📋 章節下拉選單
- 🏆 達標獎勵系統（家長後台彈性開關）
- 📊 月度家庭報告
"""

import streamlit as st
import sqlite3
import json
import random
import base64
from datetime import datetime, date, timedelta
from pathlib import Path
from contextlib import contextmanager

# ============================================================
# 0. 個人化設定（從 Secrets 讀取）
# ============================================================

def get_user_config():
    return {
        "STUDENT_NAME": st.secrets.get("STUDENT_NAME", "同學"),
        "SCHOOL_NAME": st.secrets.get("SCHOOL_NAME", ""),
        "EXAM_YEAR": st.secrets.get("EXAM_YEAR", "116"),
        "EXAM_DATE_STR": st.secrets.get("EXAM_DATE", "2027-01-22"),
        "DEFAULT_GRADE": st.secrets.get("DEFAULT_GRADE", "高二"),
        "TEXTBOOK_JSON": st.secrets.get("TEXTBOOK_JSON", ""),
        "APP_PASSWORD": st.secrets.get("APP_PASSWORD", ""),
        "PARENT_PASSWORD": st.secrets.get("PARENT_PASSWORD", ""),
    }

USER = get_user_config()
STUDENT_NAME = USER["STUDENT_NAME"]
SCHOOL_NAME = USER["SCHOOL_NAME"]
EXAM_YEAR = USER["EXAM_YEAR"]
APP_PASSWORD = USER["APP_PASSWORD"]
PARENT_PASSWORD = USER["PARENT_PASSWORD"]
NICKNAME = f"Hi {STUDENT_NAME[:1]}~"

try:
    EXAM_DATE = datetime.strptime(USER["EXAM_DATE_STR"], "%Y-%m-%d").date()
except:
    EXAM_DATE = date(2027, 1, 22)

START_DATE = date(2026, 5, 2)
USD_TO_TWD = 32  # 匯率

# ============================================================
# 1. 應用程式設定
# ============================================================

st.set_page_config(
    page_title=f"{NICKNAME} 學測導航",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---- 預設教科書版本 ----
DEFAULT_TEXTBOOK = {
    "國文": {"高二": "通用版", "高三": "通用版"},
    "英文": {"高二": "通用版", "高三": "通用版"},
    "數學B": {"高二": "通用版", "高三": "通用版"},
    "數學A": {"高二": "通用版", "高三": "通用版"},
    "物理": {"高二": "通用版", "高三": "通用版"},
    "化學": {"高二": "通用版", "高三": "通用版"},
    "生物": {"高二": "通用版", "高三": "通用版"},
    "歷史": {"高二": "通用版", "高三": "通用版"},
    "地理": {"高二": "通用版", "高三": "通用版"},
    "公民": {"高二": "通用版", "高三": "通用版"},
}

try:
    if USER["TEXTBOOK_JSON"]:
        TEXTBOOK = json.loads(USER["TEXTBOOK_JSON"])
        # 補上學測科目（若 Secrets 沒有）
        for sub, default in DEFAULT_TEXTBOOK.items():
            if sub not in TEXTBOOK:
                TEXTBOOK[sub] = default
    else:
        TEXTBOOK = DEFAULT_TEXTBOOK
except:
    TEXTBOOK = DEFAULT_TEXTBOOK

ALL_SUBJECTS = ["國文", "英文", "數學B", "數學A", "物理", "化學", "生物", "歷史", "地理", "公民"]
EXAM_SUBJECTS = ["國文", "英文", "數學A", "物理", "化學", "生物", "歷史", "地理", "公民"]  # 學測重點

# ---- 章節資料庫（學測九科 + 數學雙軌）----
CHAPTERS = {
    "國文": {
        "高二": ["📌 第二次段考範圍", "L1 古文觀止選讀", "L2 現代散文選讀", "L3 現代詩選讀",
                "L4 古典詩詞（唐詩宋詞）", "L5 文化經典（論語、孟子）", "L6 應用文與作文",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "L1 史傳文選讀", "L2 議論文選讀", "L3 哲思散文",
                "L4 文化經典（莊子、史記）", "L5 文學批評與賞析", "L6 學測作文衝刺",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
    "英文": {
        "高二": ["📌 第二次段考範圍", "Unit 1 — Reading & Vocabulary", "Unit 2 — Tenses",
                "Unit 3 — Conditional Sentences", "Unit 4 — Passive Voice", "Unit 5 — Relative Clauses",
                "Unit 6 — Cloze Test", "📝 短文寫作", "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "Unit 1 — 學測閱讀測驗", "Unit 2 — 進階句型",
                "Unit 3 — 圖表題", "Unit 4 — 翻譯題", "Unit 5 — 看圖寫作", "Unit 6 — 學測模擬卷",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
    "數學B": {
        "高二": ["📌 第二次段考範圍", "三角函數（基礎）", "三角恆等式", "直線與圓",
                "平面向量", "機率（基礎）", "統計（基礎）", "數列與級數",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "矩陣（基礎）", "二次曲線", "機率（進階）",
                "統計（信賴區間）", "🌐 學測 B 重點", "🌐 全範圍混合", "✏️ 自訂"],
    },
    "數學A": {
        "高二": ["📌 學測常考重點", "三角函數（含進階公式）", "三角恆等式（深入）",
                "直線與圓", "平面向量", "空間向量（A 限定）", "矩陣（含特徵值）",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 學測常考重點", "矩陣（進階）", "二次曲線", "機率（條件、貝氏）",
                "統計（信賴區間、迴歸）", "微分（極限、導數）", "積分（基礎）",
                "🌐 學測歷屆題型", "🌐 全範圍混合", "✏️ 自訂"],
    },
    "物理": {
        "高二": ["📌 第二次段考範圍", "力學（牛頓三大定律）", "動量與衝量", "能量守恆",
                "圓周運動與重力", "簡諧運動", "流體力學", "熱學",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "波動學", "聲學", "光學（幾何 + 波動）",
                "電磁學（電場、磁場）", "電路與電磁感應", "近代物理（量子、原子）",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
    "化學": {
        "高二": ["📌 第二次段考範圍", "物質的組成", "化學反應與計量（莫耳）",
                "物質的狀態（氣液固溶液）", "化學反應的能量", "反應速率",
                "化學平衡", "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "酸鹼鹽（pH、緩衝）", "氧化還原",
                "電化學（電池、電解）", "有機化學（官能基）", "生物化學（糖脂蛋白）",
                "化學在生活中的應用", "🌐 學測必考實驗", "🌐 全範圍混合", "✏️ 自訂"],
    },
    "生物": {
        "高二": ["📌 第二次段考範圍", "細胞構造與功能", "遺傳（孟德爾）",
                "分子遺傳（DNA、RNA）", "演化", "生物多樣性",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "動物的構造（消化、循環）", "神經與內分泌",
                "免疫系統", "生殖與發育", "生態學", "生物科技",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
    "歷史": {
        "高二": ["📌 第二次段考範圍", "史前時代與古文明", "中國古代史（先秦至唐）",
                "中國近世史（宋元明清）", "中國近代史（晚清民國）", "台灣史（早期至日治）",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "世界古代史", "歐洲中世紀與文藝復興",
                "大航海與啟蒙運動", "工業革命與兩次世界大戰", "戰後世界（冷戰至全球化）",
                "當代議題", "🌐 全範圍混合", "✏️ 自訂"],
    },
    "地理": {
        "高二": ["📌 第二次段考範圍", "地理技能（地圖、GIS）", "自然地理（地形氣候）",
                "人文地理（人口、產業、都市）", "區域地理（亞洲）",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "區域地理（歐洲、非洲）", "區域地理（美洲、大洋洲）",
                "全球議題（氣候、糧食）", "永續發展", "地理時事題（圖表判讀）",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
    "公民": {
        "高二": ["📌 第二次段考範圍", "自我與社會", "民主政治（政府、選舉）",
                "法律與生活（憲、刑、民）", "經濟學基礎（供需、市場）",
                "🌐 全範圍混合", "✏️ 自訂"],
        "高三": ["📌 第二次段考範圍", "國際關係", "全球化議題",
                "經濟學進階（GDP、貨幣）", "永續發展與社會責任", "時事分析（學測考古）",
                "🌐 全範圍混合", "✏️ 自訂"],
    },
}


def get_chapters(subject, grade):
    """取得章節清單，並統一加上歷屆學測考古題選項"""
    try:
        chapters = list(CHAPTERS[subject][grade])
    except KeyError:
        chapters = ["📌 預設範圍", "🌐 全範圍混合"]
    
    # 統一在最後加上歷屆學測考古題（每科都有）
    exam_options = [
        "📰 歷屆學測（近 5 年混合）",
        "📰 114 年學測仿題",
        "📰 113 年學測仿題",
        "📰 112 年學測仿題",
        "📰 111 年學測仿題",
        "📰 110 年學測仿題",
    ]
    # 避免重複加
    for opt in exam_options:
        if opt not in chapters:
            chapters.append(opt)
    
    if "✏️ 自訂" not in chapters:
        chapters.append("✏️ 自訂")
    
    return chapters


DB_PATH = Path("study_data.db")


# ============================================================
# 2. CSS（D 儀表板風 v3.8）
# ============================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

    /* ── 全局字體 ── */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans TC', sans-serif !important;
        font-size: 15px !important;
    }

    /* ── 設計 Token ── */
    :root {
        --primary:      #1e3a5f;   /* 深藏青 */
        --primary-lt:   #2c5282;   /* 淺藏青 */
        --accent:       #d97757;   /* 暖橙 */
        --success:      #4a7c59;   /* 苔綠 */
        --warning:      #c08827;   /* 琥珀 */
        --danger:       #b94040;   /* 磚紅 */
        --bg:           #ffffff;   /* 純白 */
        --bg-soft:      #f9fafb;   /* 淡灰白 */
        --border:       #d6d6d8;   /* 細邊框 */
        --text:         #111827;   /* 深字 */
        --text-muted:   #6b7280;   /* 灰字 */
        --radius:       6px;
    }

    /* ── 主內容區 ── */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1100px !important;
    }

    /* ── 標題 ── */
    h1 { font-size: 24px !important; font-weight: 600 !important;
         color: var(--text) !important; margin-bottom: 4px !important; }
    h2 { font-size: 20px !important; font-weight: 600 !important;
         color: var(--text) !important; margin-bottom: 4px !important; }
    h3 { font-size: 17px !important; font-weight: 500 !important;
         color: var(--text) !important; margin-bottom: 4px !important; }
    h4, h5 { font-size: 15px !important; font-weight: 500 !important;
              color: var(--text) !important; }

    /* ── Metric 卡片 ── */
    [data-testid="stMetricValue"]  { font-size: 28px !important; font-weight: 600 !important; color: var(--text) !important; }
    [data-testid="stMetricLabel"]  { font-size: 14px !important; color: var(--text-muted) !important; }
    [data-testid="stMetricDelta"]  { font-size: 13px !important; }

    /* ── 按鈕（預設：細邊框透明） ── */
    .stButton > button {
        background: var(--bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 0.4rem 0.9rem !important;
        transition: all 0.15s ease !important;
        font-family: 'Inter', 'Noto Sans TC', sans-serif !important;
    }
    .stButton > button:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        background: #eff6ff !important;
    }
    /* Primary 按鈕（深藏青） */
    .stButton > button[kind="primary"] {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--primary-lt) !important;
        border-color: var(--primary-lt) !important;
        color: white !important;
    }

    /* ── 側邊欄 ── */
    [data-testid="stSidebar"] {
        background: #f9fafb !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 13px !important;
        color: var(--text) !important;
    }

    /* ── Radio（功能選單） ── */
    [data-testid="stRadio"] > div { gap: 2px !important; }

    /* ── 輸入框 ── */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-size: 13px !important;
        background: var(--bg) !important;
    }

    /* ── 進度條 ── */
    .progress-bar {
        background: #e5e7eb;
        border-radius: 99px;
        height: 8px;
        overflow: hidden;
        margin: 4px 0;
    }
    .progress-fill {
        background: var(--primary);
        height: 100%;
        border-radius: 99px;
        transition: width 0.4s;
        display: flex; align-items: center;
        justify-content: flex-end;
        padding-right: 4px;
        color: white; font-size: 10px; font-weight: 600;
    }

    /* ── Info card ── */
    .info-card {
        background: var(--bg-soft);
        border-left: 3px solid var(--primary);
        padding: 8px 12px;
        border-radius: var(--radius);
        margin: 6px 0;
        font-size: 13px;
        color: var(--text);
    }

    /* ── 分隔線 ── */
    hr { border: none; border-top: 1px solid var(--border) !important; margin: 12px 0 !important; }

    /* ── 隱藏 Streamlit 系統 UI ── */
    button[kind="header"]           { display: none !important; }
    [data-testid="stToolbar"]       { display: none !important; }
    [data-testid="stDecoration"]    { display: none !important; }
    footer                          { visibility: hidden !important; }
    #MainMenu                       { visibility: hidden !important; }
    .stDeployButton                 { display: none !important; }

</style>

<link rel="apple-touch-icon" href="https://emojicdn.elk.sh/🎓?style=apple">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="AI Tutor">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)


# ============================================================
# 3. SQLite 資料庫
# ============================================================

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS wrong_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, subject TEXT NOT NULL, topic TEXT,
            question TEXT NOT NULL, my_answer TEXT, correct_answer TEXT,
            note TEXT, reviewed INTEGER DEFAULT 0, review_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS score_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, subject TEXT NOT NULL, score INTEGER NOT NULL,
            exam_type TEXT, note TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, subject TEXT,
            questions_done INTEGER DEFAULT 0, minutes_spent INTEGER DEFAULT 0, note TEXT
        );
        CREATE TABLE IF NOT EXISTS cat_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploaded_at TEXT NOT NULL, photo_data BLOB NOT NULL, caption TEXT
        );
        CREATE TABLE IF NOT EXISTS cat_profile (
            id INTEGER PRIMARY KEY, cat_name TEXT, cat_personality TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, engine TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS parent_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS achievement_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL, condition_name TEXT, achieved INTEGER, note TEXT
        );
        """)


def get_setting(key, default=""):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM parent_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO parent_settings (key, value) VALUES (?,?)", (key, str(value)))


def add_wrong(subject, topic, question, my_ans, correct_ans, note):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO wrong_book (date, subject, topic, question, my_answer, correct_answer, note) VALUES (?,?,?,?,?,?,?)",
            (str(date.today()), subject, topic, question, my_ans, correct_ans, note))


def get_wrongs(subject=None, only_unreviewed=True):
    with get_db() as conn:
        sql = "SELECT * FROM wrong_book WHERE 1=1"
        params = []
        if subject:
            sql += " AND subject=?"
            params.append(subject)
        if only_unreviewed:
            sql += " AND reviewed=0"
        sql += " ORDER BY date DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def mark_reviewed(wrong_id):
    with get_db() as conn:
        conn.execute("UPDATE wrong_book SET reviewed=1, review_count=review_count+1 WHERE id=?", (wrong_id,))


def add_score(subject, score, exam_type, note):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO score_log (date, subject, score, exam_type, note) VALUES (?,?,?,?,?)",
            (str(date.today()), subject, score, exam_type, note))


def get_scores(subject=None):
    with get_db() as conn:
        if subject:
            return [dict(r) for r in conn.execute("SELECT * FROM score_log WHERE subject=? ORDER BY date DESC", (subject,)).fetchall()]
        return [dict(r) for r in conn.execute("SELECT * FROM score_log ORDER BY date DESC").fetchall()]


def log_daily(subject, q_count, minutes, note=""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO daily_log (date, subject, questions_done, minutes_spent, note) VALUES (?,?,?,?,?)",
            (str(date.today()), subject, q_count, minutes, note))


def get_today_done():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT subject, SUM(questions_done) as qs, SUM(minutes_spent) as mins FROM daily_log WHERE date=? GROUP BY subject",
            (str(date.today()),)).fetchall()
        return [dict(r) for r in rows]


def get_month_stats():
    """取得本月（自然月 5/1~5/31）的學習統計"""
    month_start = date.today().replace(day=1)
    with get_db() as conn:
        row = conn.execute(
            "SELECT SUM(questions_done) as total_q, SUM(minutes_spent) as total_m FROM daily_log WHERE date>=?",
            (str(month_start),)).fetchone()
        return {
            "questions": row["total_q"] or 0,
            "minutes": row["total_m"] or 0,
        }


def export_db_json():
    data = {}
    with get_db() as conn:
        for table in ["wrong_book", "score_log", "daily_log", "cat_profile", "achievement_log"]:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(r) for r in rows]
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def add_cat_photo(photo_bytes, caption=""):
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM cat_photos").fetchone()[0]
        if count >= 6:
            conn.execute("DELETE FROM cat_photos WHERE id = (SELECT MIN(id) FROM cat_photos)")
        conn.execute(
            "INSERT INTO cat_photos (uploaded_at, photo_data, caption) VALUES (?,?,?)",
            (str(datetime.now()), photo_bytes, caption))


def get_cat_photos():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cat_photos ORDER BY id DESC").fetchall()]


def delete_cat_photo(photo_id):
    with get_db() as conn:
        conn.execute("DELETE FROM cat_photos WHERE id=?", (photo_id,))


def get_cat_profile():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cat_profile WHERE id=1").fetchone()
        if row:
            return dict(row)
        return {
            "cat_name": st.secrets.get("CAT_NAME", "小貓"),
            "cat_personality": st.secrets.get("CAT_PERSONALITY", "可愛溫暖的貓咪"),
        }


def save_cat_profile(name, personality):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cat_profile (id, cat_name, cat_personality, updated_at) VALUES (1,?,?,?)",
            (name, personality, str(datetime.now())))


def get_streak_days(daily_target):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT date, SUM(questions_done) as total
            FROM daily_log GROUP BY date ORDER BY date DESC LIMIT 30
        """).fetchall()
    streak = 0
    today = date.today()
    for r in rows:
        row_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
        if row_date == today - timedelta(days=streak) and (r["total"] or 0) >= daily_target:
            streak += 1
        else:
            break
    return streak


PRICING = {
    "Claude": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "Gemini": {"input": 1.25 / 1_000_000, "output": 5.0 / 1_000_000},
}


def log_api_usage(engine, input_tokens, output_tokens):
    cost = (input_tokens * PRICING[engine]["input"] + output_tokens * PRICING[engine]["output"])
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_usage (date, engine, input_tokens, output_tokens, estimated_cost_usd) VALUES (?,?,?,?,?)",
            (str(date.today()), engine, input_tokens, output_tokens, cost))
    return cost


def get_usage_stats():
    """以自然月計算（5/1~5/31）"""
    month_start = date.today().replace(day=1)
    with get_db() as conn:
        today_cost = conn.execute(
            "SELECT SUM(estimated_cost_usd) FROM api_usage WHERE date=?",
            (str(date.today()),)).fetchone()[0] or 0
        month_cost = conn.execute(
            "SELECT SUM(estimated_cost_usd) FROM api_usage WHERE date>=?",
            (str(month_start),)).fetchone()[0] or 0
        today_calls = conn.execute(
            "SELECT COUNT(*) FROM api_usage WHERE date=?",
            (str(date.today()),)).fetchone()[0]
    return {
        "today_usd": today_cost,
        "today_twd": today_cost * USD_TO_TWD,
        "month_usd": month_cost,
        "month_twd": month_cost * USD_TO_TWD,
        "today_calls": today_calls,
    }


init_db()


# ============================================================
# 4. 密碼驗證機制
# ============================================================

def check_app_password():
    """主 App 登入密碼驗證"""
    if not APP_PASSWORD:
        return True  # 沒設密碼就直接放行
    
    if st.session_state.get("app_authenticated"):
        return True
    
    # 顯示登入畫面（大字版）
    st.markdown("""
    <div style="max-width:480px; margin:80px auto 24px; padding:40px 36px; background:white;
                border-radius:12px; text-align:center; border:1px solid #d6d6d8;
                box-shadow:0 4px 20px rgba(0,0,0,0.06);">
        <div style="font-size:60px; margin-bottom:12px;">🎓</div>
        <div style="font-size:26px; font-weight:600; color:#1e3a5f; margin-bottom:6px;">學測導航</div>
        <div style="font-size:15px; color:#6b7280;">請輸入密碼進入</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input(
            "密碼", type="password", key="app_pwd_input",
            label_visibility="collapsed",
            placeholder="請輸入密碼",
            help="請輸入您的學習密碼"
        )
        if st.button("🔓 進入 App", type="primary", use_container_width=True):
            if password == APP_PASSWORD:
                st.session_state.app_authenticated = True
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請再試一次")

    return False


def check_parent_password():
    """家長後台密碼驗證"""
    if st.session_state.get("parent_authenticated"):
        return True
    
    st.markdown("### 🔐 家長後台登入")
    st.caption("此區域僅供家長使用")
    
    password = st.text_input("家長密碼", type="password", key="parent_pwd_input")
    if st.button("🔓 進入家長後台", type="primary"):
        if password == PARENT_PASSWORD and PARENT_PASSWORD:
            st.session_state.parent_authenticated = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤，僅家長能進入")
    
    return False


# 檢查主 App 密碼
if not check_app_password():
    st.stop()


# ============================================================
# 5. 學習階段判定（含混合策略）
# ============================================================

def get_phase(today=None):
    if today is None:
        today = date.today()
    days_left = max((EXAM_DATE - today).days, 0)
    days_passed = max((today - START_DATE).days, 0)
    total_days = (EXAM_DATE - START_DATE).days
    progress_pct = min(int(days_passed / total_days * 100), 100)

    if today < date(2026, 7, 1):
        # Phase 1：5-6 月
        return {
            "phase": "Phase 1 · 基礎期", "focus": "9 科段考準備 + 補弱點",
            "daily_target": 25, "subjects": ALL_SUBJECTS,  # 9 科都要
            "days_left": days_left, "progress_pct": progress_pct, "emoji": "🌱",
            "strategy": "跟學校進度走，平日 9 科都要顧",
        }
    elif today < date(2026, 10, 1):
        # Phase 2：暑假
        return {
            "phase": "Phase 2 · 衝刺期", "focus": "學測 5 科火力集中",
            "daily_target": 50, "subjects": EXAM_SUBJECTS,  # 學測重點
            "days_left": days_left, "progress_pct": progress_pct, "emoji": "🔥",
            "strategy": "全範圍重新梳理，火力集中（決勝負期）",
        }
    elif today < date(2026, 12, 25):
        # Phase 3：模考
        return {
            "phase": "Phase 3 · 模擬期", "focus": "學測歷屆題 + 計時訓練",
            "daily_target": 60, "subjects": EXAM_SUBJECTS,
            "days_left": days_left, "progress_pct": progress_pct, "emoji": "⚡",
            "strategy": "歷屆學測 + 模擬考訓練",
        }
    else:
        # Phase 4：精修
        return {
            "phase": "Phase 4 · 決勝期", "focus": "錯題本回顧 + 心態維持",
            "daily_target": 20, "subjects": EXAM_SUBJECTS,
            "days_left": days_left, "progress_pct": progress_pct, "emoji": "🎯",
            "strategy": "只回顧錯題本，保持手感",
        }


# ============================================================
# 6. AI 引擎（升級到 Gemini 2.0）
# ============================================================

@st.cache_resource
def get_claude_client():
    try:
        from anthropic import Anthropic
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return Anthropic(api_key=api_key)
    except ImportError:
        return None


@st.cache_resource
def get_gemini_model():
    """Gemini 模型載入（用 2026 主推穩定版）"""
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        # 2026 主推穩定版
        return genai.GenerativeModel("gemini-2.5-flash")
    except ImportError:
        return None


# Gemini 模型備援清單（2026 經查證可用版本，按優先順序）
GEMINI_MODEL_CANDIDATES = [
    "gemini-2.5-flash",          # 2026 主推穩定版（最佳）
    "gemini-2.5-flash-lite",     # 超快、超便宜備援
    "gemini-2.0-flash",          # 經典版本（仍支援舊用戶）
    "gemini-2.0-flash-001",      # 帶版本號
    "gemini-1.5-flash",          # 最終備援
    "gemini-1.5-flash-latest",   # latest alias
]


def call_gemini_with_fallback(prompt, system):
    """嘗試多個 Gemini 模型，直到成功"""
    import google.generativeai as genai
    last_error = None
    for model_name in GEMINI_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name, system_instruction=system)
            response = model.generate_content(prompt)
            return response, model_name
        except Exception as e:
            last_error = f"{model_name}: {type(e).__name__}"
            continue
    raise Exception(f"所有 Gemini 模型都失敗。最後錯誤：{last_error}")


def ask_ai(prompt, system="", engine="Gemini"):
    default_system = f"你是一位資深的台灣高中升大學家教老師，熟悉 108 課綱與大學學測歷屆題型。學生暱稱「{NICKNAME}」。回答用繁體中文，內容要清楚、有條理、有解題思路。"
    system = system or default_system

    usage = get_usage_stats()
    monthly_limit = float(st.secrets.get("MONTHLY_BUDGET_USD", "20"))
    if usage["month_usd"] >= monthly_limit:
        return f"⚠️ 已達本月 API 預算上限 NT${monthly_limit*USD_TO_TWD:.0f}（目前已用 NT${usage['month_twd']:.0f}）。請等下個月或請家長調整預算。"

    if engine == "Claude":
        client = get_claude_client()
        if not client:
            return "❌ 尚未設定 ANTHROPIC_API_KEY，請至 Settings → Secrets 新增。"
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            log_api_usage("Claude", msg.usage.input_tokens, msg.usage.output_tokens)
            return msg.content[0].text
        except Exception as e:
            return f"❌ Claude 錯誤：{type(e).__name__} — {str(e)}"
    else:
        model = get_gemini_model()
        if not model:
            return "❌ 尚未設定 GOOGLE_API_KEY，請至 Settings → Secrets 新增。"
        try:
            response, used_model = call_gemini_with_fallback(prompt, system)
            try:
                in_tokens = response.usage_metadata.prompt_token_count
                out_tokens = response.usage_metadata.candidates_token_count
            except:
                in_tokens = len(prompt) // 3
                out_tokens = len(response.text) // 3
            log_api_usage("Gemini", in_tokens, out_tokens)
            return response.text
        except Exception as e:
            return f"❌ Gemini 連線失敗：{str(e)}\n\n💡 建議：切換到 Claude 引擎試試（如果有 Anthropic Key）。"


# ============================================================
# 7. 達標獎勵系統（家長後台控制）
# ============================================================

def get_reward_enabled():
    """獎勵系統是否啟用（家長後台控制）"""
    return get_setting("reward_enabled", "0") == "1"


def get_achievement_status():
    """計算當月達標進度"""
    month_stats = get_month_stats()
    month_target_q = int(get_setting("monthly_q_target", "600"))
    
    # 條件 1：學習量
    cond_1 = month_stats["questions"] >= month_target_q
    
    # 條件 2：學校成績進步（手動填）
    cond_2 = get_setting("month_school_improved", "0") == "1"
    
    # 條件 3：錯題複習率
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM wrong_book").fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(*) FROM wrong_book WHERE reviewed=1").fetchone()[0]
    review_rate = (reviewed / total * 100) if total > 0 else 0
    cond_3 = review_rate >= 60
    
    # 條件 4：家長心態評估
    cond_4 = get_setting("month_attitude_ok", "0") == "1"
    
    achieved_count = sum([cond_1, cond_2, cond_3, cond_4])
    
    return {
        "conditions": [
            {"name": "學習量達標", "achieved": cond_1, "detail": f"{month_stats['questions']}/{month_target_q} 題"},
            {"name": "學校成績進步", "achieved": cond_2, "detail": "由家長標記"},
            {"name": "錯題複習率 ≥ 60%", "achieved": cond_3, "detail": f"{review_rate:.0f}%"},
            {"name": "心態狀態良好", "achieved": cond_4, "detail": "由家長評估"},
        ],
        "achieved_count": achieved_count,
        "total": 4,
        "is_great": achieved_count >= 4,
        "is_good": achieved_count >= 3,
    }


# ============================================================
# 8. 側邊欄
# ============================================================

CAT_PHOTOS_DIR = Path("cat_photos")


def get_builtin_cat_photos():
    media = []
    if CAT_PHOTOS_DIR.exists() and CAT_PHOTOS_DIR.is_dir():
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.gif"):
            media.extend(sorted(CAT_PHOTOS_DIR.glob(ext)))
        for ext in ("*.mp4", "*.webm", "*.mov"):
            media.extend(sorted(CAT_PHOTOS_DIR.glob(ext)))
    return media


def is_video(file_path):
    return str(file_path).lower().endswith(('.mp4', '.webm', '.mov'))


def get_media_mime(file_path):
    ext = str(file_path).lower().split('.')[-1]
    return {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'webp': 'image/webp', 'gif': 'image/gif',
        'mp4': 'video/mp4', 'webm': 'video/webm', 'mov': 'video/quicktime',
    }.get(ext, 'application/octet-stream')


phase_info = get_phase()

with st.sidebar:
    cat_profile = get_cat_profile()
    cat_photos = get_cat_photos()
    builtin_photos = get_builtin_cat_photos()
    streak = get_streak_days(phase_info["daily_target"])

    photo_b64 = None
    media_type = "image"
    media_mime = "image/jpeg"
    all_options = []

    for p in builtin_photos:
        all_options.append(("builtin", p))
    for p in cat_photos:
        all_options.append(("uploaded", p))

    if all_options:
        source_type, chosen = random.choice(all_options)
        if source_type == "builtin":
            with open(chosen, "rb") as f:
                photo_b64 = base64.b64encode(f.read()).decode()
            media_type = "video" if is_video(chosen) else "image"
            media_mime = get_media_mime(chosen)
        else:
            photo_b64 = base64.b64encode(chosen["photo_data"]).decode()
            media_type = "image"
            media_mime = "image/jpeg"

    if photo_b64:
        today_done = sum(t["qs"] or 0 for t in get_today_done())
        target = phase_info["daily_target"]
        cat_name = cat_profile["cat_name"]
        if today_done >= target:
            cat_mood = "😻"
            cat_says = f"{NICKNAME} 今天好棒！已完成 {today_done} 題～"
        elif today_done >= target * 0.5:
            cat_says = f"喵～繼續加油！還差 {target - today_done} 題達標！"
            cat_mood = "🐱"
        elif today_done > 0:
            cat_says = f"喵嗚～你已做了 {today_done} 題，再 push 一下！"
            cat_mood = "😺"
        else:
            cat_says = f"Hi {STUDENT_NAME[:1]}，{cat_name} 在等你開始念書喔！"
            cat_mood = "😿"

        if media_type == "video":
            media_html = f'<video autoplay loop muted playsinline style="width:110px; height:110px; object-fit:cover; border-radius:50%; border:3px solid #ff6b35; box-shadow:0 4px 10px rgba(0,0,0,0.1);"><source src="data:{media_mime};base64,{photo_b64}" type="{media_mime}"></video>'
        else:
            media_html = f'<img src="data:{media_mime};base64,{photo_b64}" style="width:110px; height:110px; object-fit:cover; border-radius:50%; border:3px solid #ff6b35; box-shadow:0 4px 10px rgba(0,0,0,0.1);">'

        streak_html = f'<div style="margin-top:5px; font-size:11px; color:#ff6b35; font-weight:bold;">🔥 連續達標 {streak} 天</div>' if streak > 0 else ''

        sidebar_html = (
            f'<div style="text-align:center; padding:10px; background:linear-gradient(135deg,#fff3e0,#ffe0b2); border-radius:10px; margin-bottom:10px;">'
            f'{media_html}'
            f'<div style="margin-top:6px; font-weight:bold; color:#d84315; font-size:14px;">{cat_mood} {cat_name}</div>'
            f'<div style="font-size:12px; color:#5d4037; margin-top:3px; padding:0 6px;">"{cat_says}"</div>'
            f'{streak_html}'
            f'</div>'
        )
        st.markdown(sidebar_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center; padding:16px; background:#fff3e0; border-radius:10px; margin-bottom:10px;">'
            '<div style="font-size:36px;">🐱</div>'
            '<div style="font-size:12px; color:#5d4037; margin-top:6px;">到「🐱 我的貓咪」上傳照片！</div>'
            '</div>', unsafe_allow_html=True)

    # 標題（拆兩行）
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="font-size:20px; font-weight:600; color:#111827; line-height:1.2;">🎓 {NICKNAME}</div>
        <div style="font-size:13px; color:#6b7280; margin-top:2px;">學測導航</div>
    </div>
    """, unsafe_allow_html=True)

    # AI 引擎切換（拆兩行，標示免費 vs 計費）
    engine = st.radio(
        "AI 引擎",
        ["Gemini", "Claude"],
        format_func=lambda x: "🟢 Gemini（免費）" if x == "Gemini" else "🔴 Claude（計費）",
        help="Gemini：免費、速度快｜Claude：題目品質高、計費",
        horizontal=False,
    )

    usage = get_usage_stats()
    if usage["today_calls"] > 0:
        st.caption(f"📊 今日 {usage['today_calls']} 次 | NT${usage['today_twd']:.0f}")

    st.divider()

    # 年級 + 科目選擇
    grade = st.selectbox("年級", ["高二", "高三"], index=0 if USER["DEFAULT_GRADE"] == "高二" else 1)
    
    # 顯示哪些科目（依階段）
    available_subjects = phase_info["subjects"]
    subject = st.selectbox("科目", available_subjects)
    
    publisher = TEXTBOOK.get(subject, {}).get(grade, "通用版")

    # 學校名顯示簡化：「中信高中」→「高中」（保留辨識度但去除具體校名）
    school_label = ""
    if SCHOOL_NAME:
        if "高中" in SCHOOL_NAME:
            school_label = "高中 "
        elif "國中" in SCHOOL_NAME:
            school_label = "國中 "
        else:
            school_label = ""  # 其他情況不顯示
    st.markdown(f'<div class="info-card">📚 {school_label}<b>{publisher}版</b><br>{grade} {subject}</div>', unsafe_allow_html=True)

    st.divider()

    PAGE_OPTIONS = ["🏠 首頁", "📝 刷題練習", "🧠 蘇格拉底引導",
                    "📓 錯題本", "📊 進度追蹤", "🐱 我的貓咪",
                    "💰 費用監控", "💾 資料備份", "🔐 家長後台"]
    
    # 如果有「跳轉到首頁」的請求，預設選首頁
    default_page_idx = 0
    if "current_page" in st.session_state:
        try:
            default_page_idx = PAGE_OPTIONS.index(st.session_state.current_page)
        except ValueError:
            default_page_idx = 0
    
    page = st.radio(
        "功能選單",
        PAGE_OPTIONS,
        index=default_page_idx,
        key="page_radio",
    )
    st.session_state.current_page = page


# ============================================================
# 9. 頂部資訊欄（精簡版）
# ============================================================

st.markdown(f"""
<div style="background:#1e3a5f; color:white; padding:14px 20px; border-radius:8px; margin-bottom:14px;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div>
            <div style="font-size:11px; opacity:0.75; margin-bottom:2px;">距 {EXAM_YEAR} 學測</div>
            <div style="font-size:28px; font-weight:700; line-height:1;">{phase_info['days_left']} <span style="font-size:14px; font-weight:400; opacity:0.85;">天</span></div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:11px; opacity:0.75; margin-bottom:4px;">{phase_info['phase']}</div>
            <div style="font-size:13px; font-weight:500; background:rgba(255,255,255,0.15); padding:4px 12px; border-radius:99px;">{phase_info['focus']}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:11px; opacity:0.75; margin-bottom:2px;">每日目標</div>
            <div style="font-size:28px; font-weight:700; line-height:1;">{phase_info['daily_target']} <span style="font-size:14px; font-weight:400; opacity:0.85;">題</span></div>
        </div>
    </div>
    <div style="margin-top:10px; background:rgba(255,255,255,0.2); border-radius:99px; height:4px;">
        <div style="width:{phase_info['progress_pct']}%; height:100%; background:rgba(255,255,255,0.8); border-radius:99px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# 10. 頁面分流
# ============================================================

# 「🏠 回首頁」按鈕（除了首頁本身，其他頁面都顯示）
if page != "🏠 首頁":
    col_home1, col_home2 = st.columns([5, 1])
    with col_home2:
        if st.button("🏠 回首頁", key="back_home_top", use_container_width=True, type="secondary"):
            # 清掉刷題狀態避免殘留
            for key in ["quiz_state", "quiz_data", "user_answers", "quiz_start_time", 
                        "quiz_end_time", "score_logged", "socratic_history", 
                        "socratic_question", "socratic_system"]:
                if key in st.session_state:
                    del st.session_state[key]
            # 強制切換到首頁
            st.session_state.current_page = "🏠 首頁"
            # 也要重設 radio 的 widget state
            if "page_radio" in st.session_state:
                del st.session_state.page_radio
            st.rerun()

# ---------- 🏠 首頁（今日任務） ----------
if page == "🏠 首頁":
    st.header(f"🏠 {NICKNAME}，今天該做什麼？")

    today_done = get_today_done()
    total_done = sum(t["qs"] or 0 for t in today_done)
    total_mins = sum(t["mins"] or 0 for t in today_done)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日題數", f"{total_done}", f"目標 {phase_info['daily_target']}")
    with col2:
        st.metric("今日讀書", f"{total_mins} 分", f"{total_mins // 60} 小時")
    with col3:
        completion = min(int(total_done / phase_info['daily_target'] * 100), 100) if phase_info['daily_target'] else 0
        st.metric("完成度", f"{completion}%", "💪 加油" if completion < 100 else "✅ 達標")

    # 顯示獎勵進度（如果家長啟用）
    if get_reward_enabled():
        st.divider()
        st.subheader("🏆 本月達標進度")
        ach = get_achievement_status()
        for cond in ach["conditions"]:
            icon = "✅" if cond["achieved"] else "⏳"
            st.markdown(f"{icon} **{cond['name']}** — {cond['detail']}")
        
        st.markdown(f"""
        <div class="info-card" style="border-left-color: {'#10b981' if ach['is_great'] else '#f59e0b'};">
        🎯 進度：<b>{ach['achieved_count']} / 4</b>
        {' — ⭐ 月度標準達成！' if ach['is_good'] else ''}
        {' — 🏆 滿分達標！家長會看到這份努力 ❤️' if ach['is_great'] else ''}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 今日建議分配")
    weakness_subjects = []
    with get_db() as conn:
        for s in phase_info["subjects"]:
            wrong_count = conn.execute(
                "SELECT COUNT(*) FROM wrong_book WHERE subject=? AND reviewed=0", (s,)
            ).fetchone()[0]
            if wrong_count > 0:
                weakness_subjects.append((s, wrong_count))

    weakness_subjects.sort(key=lambda x: -x[1])

    if weakness_subjects:
        st.markdown("**🎯 優先複習（依錯題數排序）**")
        for s, cnt in weakness_subjects[:3]:
            st.markdown(f"- **{s}**：{cnt} 題待複習")
    else:
        st.info(f"👍 目前沒有累積錯題，到「📝 刷題練習」開始今日 {phase_info['daily_target']} 題吧！")

    st.divider()
    st.subheader("✏️ 登錄今日進度")
    with st.form("daily_log_form"):
        log_subject = st.selectbox("科目", phase_info["subjects"], key="log_sub")
        col_a, col_b = st.columns(2)
        with col_a:
            log_qs = st.number_input("做了幾題", 0, 200, 10)
        with col_b:
            log_mins = st.number_input("花了幾分鐘", 0, 600, 30)
        log_note = st.text_input("備註（選填）", placeholder="例如：第三章三角函數複習")
        if st.form_submit_button("💾 記錄今日進度", type="primary"):
            log_daily(log_subject, log_qs, log_mins, log_note)
            st.success("✅ 已記錄！繼續加油！")
            st.rerun()


# ---------- 📝 刷題練習 (v3.7 真考試模式) ----------
elif page == "📝 刷題練習":
    # 狀態管理
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = "setup"
    if "quiz_data" not in st.session_state:
        st.session_state.quiz_data = None
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "quiz_start_time" not in st.session_state:
        st.session_state.quiz_start_time = None
    if "quiz_end_time" not in st.session_state:
        st.session_state.quiz_end_time = None

    # ===== 階段 1：設定 =====
    if st.session_state.quiz_state == "setup":
        st.header(f"📝 {publisher}版 {grade}{subject}")
        st.caption("真實考試模式 · 作答 → 交卷 → 評分 → 一鍵加錯題本")
        
        if subject == "數學A" and date.today() < date(2026, 7, 1):
            st.info("💡 您正在練「數學 A」進階題（學測進階）。學校段考用「數學 B」喔！")
        elif subject == "數學B":
            st.info("💡 您正在練「數學 B」（學校段考用）。暑假後可以加練「數學 A」拚學測進階題！")

        last_scores = get_scores(subject)
        boost_hint = ""
        if last_scores and last_scores[0]["score"] < 80:
            last = last_scores[0]
            boost_hint = f"（{NICKNAME} 上次 {subject} 得分 {last['score']} 分。請出修正強化版題目。）"
            st.warning(f"📈 偵測到上次 {subject} 得 {last['score']} 分，已開啟「進步衝刺模式」")

        chapter_options = get_chapters(subject, grade)
        
        st.markdown("##### ⚙️ 考試設定")
        col1, col2 = st.columns([2, 1])
        with col1:
            chapter_choice = st.selectbox(
                "📌 範圍/章節 *（必選）",
                chapter_options,
                help="選擇章節讓 AI 出精準題目"
            )
            if chapter_choice == "✏️ 自訂":
                chapter = st.text_input("自訂章節內容", placeholder="例如：第三章 三角函數和角公式")
            else:
                chapter = chapter_choice
        
        with col2:
            difficulty = st.selectbox("📊 難度 *（必選）", ["基礎", "中等", "進階", "挑戰學測"])

        col3, col4 = st.columns(2)
        with col3:
            num_q = st.slider("📝 題數", 5, 20, 10, help="建議 10 題，適合 15-20 分鐘作答")
        with col4:
            time_limit = st.selectbox(
                "⏰ 限時（選填）", 
                ["不限時", "10 分鐘", "15 分鐘", "20 分鐘", "30 分鐘"],
                help="模擬學測時間壓力"
            )

        st.markdown("---")

        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("🚀 開始考試", type="primary", use_container_width=True):
                if not chapter or chapter == "✏️ 自訂":
                    st.warning("請先選擇章節或輸入自訂內容")
                else:
                    # 判斷是否為考古題模式
                    is_exam_mode = chapter.startswith("📰")
                    if is_exam_mode:
                        exam_context = f"""這是仿照「{chapter.replace('📰', '').strip()}」題型的練習卷。
請仿照大學學測的真實出題風格：
- 情境化、跨領域思考
- 閱讀測驗型（國文、英文）
- 計算與推理型（數學、物理、化學）
- 圖表判讀型（地理、公民）
- 難度與真實學測相當（選項設計精細、容易混淆）
"""
                    else:
                        exam_context = "仿學測 108 課綱題型，情境化、有思考深度"

                    prompt = f"""你是台灣高中升大學家教，熟悉 108 課綱與歷屆學測。

請為高中生 {NICKNAME} 出 {num_q} 題「{subject}」單選題。{boost_hint}

【教材】{publisher}版 {grade}{subject}
【範圍】{chapter}
【難度】{difficulty}
【出題風格】{exam_context}

【嚴格格式】
請輸出純 JSON，**不要任何 markdown 標記**（不要 ```json），不要任何說明文字：

{{
  "quiz_title": "{chapter} - 練習卷",
  "questions": [
    {{
      "id": 1,
      "type": "single_choice",
      "question": "完整題目敘述...",
      "options": {{
        "A": "選項 A 內容",
        "B": "選項 B 內容",
        "C": "選項 C 內容",
        "D": "選項 D 內容"
      }},
      "answer": "B",
      "explanation": "詳解：解題思路、易錯點、觀念連結"
    }}
  ]
}}

【出題原則】
1. 每題必為 4 選 1 單選題（A/B/C/D）
2. 仿學測 108 課綱題型，情境化、有思考深度
3. answer 欄位只填 A/B/C/D 其中一個字母
4. explanation 要詳細，說明為什麼選這個、其他選項為何錯
5. 題目不重複，難度遞進
6. **絕對不要在 JSON 外加任何文字**
"""
                    with st.spinner(f"{engine} 正在出題中，請稍候..."):
                        result = ask_ai(prompt, engine=engine)
                        cleaned = result.strip()
                        # 移除 markdown code block
                        if cleaned.startswith("```"):
                            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                        if cleaned.endswith("```"):
                            cleaned = cleaned.rsplit("```", 1)[0]
                        cleaned = cleaned.strip()
                        # 移除非法控制字元（保留換行、tab）
                        import re
                        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
                        # 確保從 { 開始到 } 結束
                        if '{' in cleaned and '}' in cleaned:
                            start_idx = cleaned.index('{')
                            end_idx = cleaned.rindex('}') + 1
                            cleaned = cleaned[start_idx:end_idx]

                        try:
                            quiz_data = json.loads(cleaned)
                            if "questions" not in quiz_data or len(quiz_data["questions"]) == 0:
                                raise ValueError("沒有題目")

                            st.session_state.quiz_data = quiz_data
                            st.session_state.quiz_subject = subject
                            st.session_state.quiz_topic = chapter
                            st.session_state.quiz_state = "answering"
                            st.session_state.quiz_start_time = datetime.now()
                            st.session_state.user_answers = {}
                            st.session_state.quiz_time_limit = time_limit
                            st.rerun()
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            st.error("❌ AI 出題格式有誤，請再試一次（或切換 AI 引擎）")
                            with st.expander("🔍 技術細節（給家長看）"):
                                st.code(f"錯誤：{e}\n\n回應前 500 字：\n{cleaned[:500]}")

        with col_btn2:
            streak = get_streak_days(phase_info["daily_target"])
            if streak > 0:
                st.metric("🔥 連續", f"{streak} 天")

    # ===== 階段 2：作答中 =====
    elif st.session_state.quiz_state == "answering":
        quiz = st.session_state.quiz_data
        questions = quiz["questions"]
        total = len(questions)
        answered = len(st.session_state.user_answers)
        
        elapsed = datetime.now() - st.session_state.quiz_start_time
        elapsed_min = int(elapsed.total_seconds() // 60)
        elapsed_sec = int(elapsed.total_seconds() % 60)
        
        # 頂部 status bar
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("📝 進度", f"{answered}/{total}")
        with col_s2:
            st.metric("⏰ 用時", f"{elapsed_min:02d}:{elapsed_sec:02d}")
        with col_s3:
            st.metric("📚 科目", subject)
        with col_s4:
            topic_short = st.session_state.quiz_topic[:8] if st.session_state.quiz_topic else "—"
            st.metric("📊 範圍", topic_short)
        
        st.markdown("---")
        st.markdown(f"### {quiz.get('quiz_title', '練習卷')}")
        
        # 顯示所有題目
        for q in questions:
            qid = q["id"]
            st.markdown(f"##### 第 {qid} 題")
            st.markdown(q["question"])
            
            opts = q["options"]
            current = st.session_state.user_answers.get(qid)
            
            choice = st.radio(
                "選擇答案",
                options=["A", "B", "C", "D"],
                format_func=lambda x: f"{x}. {opts.get(x, '')}",
                key=f"q_{qid}",
                index=["A","B","C","D"].index(current) if current in ["A","B","C","D"] else None,
                label_visibility="collapsed",
            )
            if choice:
                st.session_state.user_answers[qid] = choice
            
            st.markdown("---")
        
        # 交卷按鈕
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if answered < total:
                st.warning(f"⚠️ 還有 {total - answered} 題未作答")
            else:
                st.success(f"✅ {total} 題全部作答完成！")
            
            if st.button(
                "📤 交卷，看分數",
                type="primary",
                use_container_width=True,
                disabled=(answered == 0)
            ):
                st.session_state.quiz_end_time = datetime.now()
                st.session_state.quiz_state = "submitted"
                duration_min = int((st.session_state.quiz_end_time - st.session_state.quiz_start_time).total_seconds() // 60)
                log_daily(subject, total, max(duration_min, 1), f"{st.session_state.quiz_topic}")
                st.rerun()
        
        with col_b:
            if st.button("🔙 放棄", use_container_width=True):
                st.session_state.quiz_state = "setup"
                st.session_state.quiz_data = None
                st.session_state.user_answers = {}
                st.rerun()

    # ===== 階段 3：已交卷，評分 + 詳解 =====
    elif st.session_state.quiz_state == "submitted":
        quiz = st.session_state.quiz_data
        questions = quiz["questions"]
        total = len(questions)
        user_ans = st.session_state.user_answers
        
        correct_count = 0
        wrong_questions = []
        for q in questions:
            qid = q["id"]
            if user_ans.get(qid) == q["answer"]:
                correct_count += 1
            else:
                wrong_questions.append(q)
        
        score = round(correct_count / total * 100)
        elapsed = st.session_state.quiz_end_time - st.session_state.quiz_start_time
        elapsed_min = int(elapsed.total_seconds() // 60)
        elapsed_sec = int(elapsed.total_seconds() % 60)
        
        if "score_logged" not in st.session_state or st.session_state.score_logged != id(quiz):
            add_score(subject, score, "AI 練習卷", f"{st.session_state.quiz_topic} ({correct_count}/{total})")
            st.session_state.score_logged = id(quiz)
        
        # 成績儀表板
        if score >= 80:
            score_color = "#10b981"
            score_emoji = "🌟"
            score_msg = "太棒了！"
        elif score >= 60:
            score_color = "#f59e0b"
            score_emoji = "💪"
            score_msg = "及格，繼續加油！"
        else:
            score_color = "#ef4444"
            score_emoji = "📚"
            score_msg = "別灰心，看看哪裡錯了！"
        
        st.markdown(f"""
        <div style="background: white; padding: 24px; border-radius: 8px; border: 1px solid #d6d6d8; margin-bottom: 16px;">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #6b7280;">考試成績</div>
                <div style="font-size: 56px; font-weight: 600; color: {score_color}; line-height: 1;">{score}<span style="font-size: 24px;"> 分</span></div>
                <div style="font-size: 14px; color: #6b7280; margin-top: 8px;">{score_emoji} {score_msg}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.metric("✅ 答對", f"{correct_count}/{total}")
        with col_r2:
            st.metric("❌ 答錯", f"{len(wrong_questions)}")
        with col_r3:
            st.metric("⏰ 用時", f"{elapsed_min:02d}:{elapsed_sec:02d}")
        with col_r4:
            avg_sec = int(elapsed.total_seconds() / total) if total else 0
            st.metric("⚡ 平均", f"{avg_sec} 秒/題")
        
        st.markdown("---")
        st.markdown("### 📋 答題明細")
        
        filter_mode = st.radio(
            "顯示",
            ["全部", "只看答錯", "只看答對"],
            horizontal=True,
            label_visibility="collapsed",
        )
        
        if wrong_questions and filter_mode != "只看答對":
            if st.button(f"📌 一鍵加入 {len(wrong_questions)} 題到錯題本", type="primary"):
                added = 0
                for q in wrong_questions:
                    qid = q["id"]
                    add_wrong(
                        subject=subject,
                        topic=st.session_state.quiz_topic,
                        question=q["question"] + "\n\n選項：\n" + "\n".join([f"{k}. {v}" for k, v in q["options"].items()]),
                        my_ans=user_ans.get(qid, "(未作答)"),
                        correct_ans=q["answer"],
                        note=q.get("explanation", "")[:200]
                    )
                    added += 1
                st.success(f"✅ 已加入 {added} 題到錯題本！")
        
        st.markdown("---")
        
        for q in questions:
            qid = q["id"]
            user_choice = user_ans.get(qid, "(未作答)")
            correct = q["answer"]
            is_correct = (user_choice == correct)
            
            if filter_mode == "只看答錯" and is_correct:
                continue
            if filter_mode == "只看答對" and not is_correct:
                continue
            
            with st.expander(f"第 {qid} 題  {'✅' if is_correct else '❌'}", expanded=not is_correct):
                st.markdown(f"**題目：** {q['question']}")
                st.markdown("**選項：**")
                for opt_key, opt_val in q["options"].items():
                    if opt_key == correct:
                        st.markdown(f"- **{opt_key}. {opt_val}** ✅ 正確答案")
                    elif opt_key == user_choice and not is_correct:
                        st.markdown(f"- ~~{opt_key}. {opt_val}~~ ❌ 您的答案")
                    else:
                        st.markdown(f"- {opt_key}. {opt_val}")
                
                st.markdown(f"**📚 詳解：** {q.get('explanation', '(無)')}")
                
                if not is_correct:
                    if st.button(f"📌 加入錯題本", key=f"add_wrong_{qid}"):
                        add_wrong(
                            subject=subject,
                            topic=st.session_state.quiz_topic,
                            question=q["question"] + "\n\n選項：\n" + "\n".join([f"{k}. {v}" for k, v in q["options"].items()]),
                            my_ans=user_choice,
                            correct_ans=correct,
                            note=q.get("explanation", "")[:200]
                        )
                        st.success("✅ 已加入錯題本！")
        
        st.markdown("---")
        
        # 行動列
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            if st.button("🔄 再來一輪", type="primary", use_container_width=True):
                st.session_state.quiz_state = "setup"
                st.session_state.quiz_data = None
                st.session_state.user_answers = {}
                if "score_logged" in st.session_state:
                    del st.session_state.score_logged
                st.rerun()
        with col_e2:
            if st.button("📓 看錯題本", use_container_width=True):
                st.session_state.quiz_state = "setup"
                st.session_state.quiz_data = None
                st.session_state.user_answers = {}
                st.rerun()
        with col_e3:
            if st.button("🏠 回主畫面", use_container_width=True):
                st.session_state.quiz_state = "setup"
                st.session_state.quiz_data = None
                st.session_state.user_answers = {}
                st.rerun()


# ---------- 🧠 蘇格拉底引導（v3.8 重設計）----------
elif page == "🧠 蘇格拉底引導":
    st.header("🧠 蘇格拉底解題引導")
    st.caption("AI 不直接給答案，用追問方式幫你自己想出來。")

    if "socratic_history" not in st.session_state:
        st.session_state.socratic_history = []
        st.session_state.socratic_question = ""

    if not st.session_state.socratic_history:
        st.markdown("##### 選擇提問方式")

        mode = st.radio(
            "提問模式",
            ["📌 從錯題本選", "📚 選預設題型", "✏️ 自由貼題目"],
            horizontal=True,
            label_visibility="collapsed",
        )

        question = ""

        # 模式 1：從錯題本選
        if mode == "📌 從錯題本選":
            wrongs = get_wrongs(only_unreviewed=True)
            if not wrongs:
                st.info("錯題本目前是空的，先去「📝 刷題練習」累積錯題吧！")
            else:
                options = {f"#{w['id']} [{w['subject']}] {w['question'][:40]}...": w for w in wrongs[:10]}
                choice_key = st.selectbox("選一題來討論", list(options.keys()))
                chosen = options[choice_key]
                question = f"""題目：{chosen['question']}

選項：
{chr(10).join([f"{k}. {v}" for k, v in (chosen.get('options_json') or {}).items()]) if chosen.get('options_json') else '（選項已略去）'}

我的答案：{chosen['my_answer']}
正確答案：{chosen['correct_answer']}
我知道我答錯了，但不確定哪裡想錯了，請引導我思考。"""
                st.markdown(f"""
                <div class="info-card">
                <b>#{chosen['id']}</b> {chosen['subject']} · {chosen['topic']}<br>
                <small>我的答案：{chosen['my_answer']} → 正確：{chosen['correct_answer']}</small>
                </div>
                """, unsafe_allow_html=True)

        # 模式 2：選預設題型
        elif mode == "📚 選預設題型":
            topic_map = {
                "📐 數學：三角函數公式應用":
                    "我在練習三角函數，請出一題「積化和差或和差化積」的應用題，然後引導我解題。",
                "📐 數學：向量內積計算":
                    "請出一題「空間向量內積與夾角」的計算題，引導我一步步算出來。",
                "📐 數學：機率條件機率":
                    "請出一題「條件機率或貝氏定理」的應用題，引導我解題。",
                "🧪 化學：莫耳計算":
                    "請出一題「莫耳數、質量、體積換算」的計算題，引導我理解每一步。",
                "🧪 化學：酸鹼中和滴定":
                    "請出一題「酸鹼中和滴定計算」題，引導我用蘇格拉底法解題。",
                "⚡ 物理：牛頓定律應用":
                    "請出一題「牛頓第二定律 F=ma」的綜合題，引導我找出每個力的方向和大小。",
                "⚡ 物理：電路分析":
                    "請出一題「串並聯電路」的分析題，引導我算出各分支的電流和電壓。",
                "📖 國文：文言文語意推斷":
                    "請出一題「文言文語意或詞義判斷」的學測題型，引導我推敲正確意思。",
                "🌍 英文：克漏字邏輯推斷":
                    "請出一題「克漏字填空」題，引導我從上下文找出最合適的答案。",
            }
            topic_choice = st.selectbox("選擇題目類型", list(topic_map.keys()))
            question = topic_map[topic_choice]
            st.info(f"💡 AI 將出一題「{topic_choice.split(' ', 1)[1]}」並引導你解題")

        # 模式 3：自由貼題目
        elif mode == "✏️ 自由貼題目":
            question = st.text_area(
                "貼上你卡住的題目",
                placeholder="把完整題目貼在這裡，越詳細越好",
                height=150,
            )

        st.markdown("---")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            if st.button("🎯 開始蘇格拉底引導", type="primary", use_container_width=True,
                         disabled=(not question)):
                st.session_state.socratic_question = question
                system_prompt = f"""你是一位耐心的高中家教老師，用蘇格拉底引導法幫 {NICKNAME} 解題。

【鐵律】
1. 絕對不可以直接給完整答案
2. 每次只問 1 個關鍵問題，引導她自己思考
3. 從她的回答判斷她卡在哪一步
4. 答對中間步驟立刻肯定她（「對！」「很好！」）
5. 答錯不直接糾正，反問「你為什麼這樣想？」
6. 語氣溫和、像鄰家姊姊，保持親切
7. 最後她答出來時，整理一遍關鍵觀念

【科目背景】現在練習的是 {subject}（{publisher}版 {grade}）
"""
                first = ask_ai(
                    f"以下是學生的問題：\n\n{question}\n\n請開始你的第一個引導問題。",
                    system=system_prompt, engine=engine,
                )
                st.session_state.socratic_history.append(("ai", first))
                st.session_state.socratic_system = system_prompt
                st.rerun()
        with col_s2:
            if question:
                st.markdown('<div style="padding-top:8px;"><small style="color:#6b7280;">✅ 題目已準備好</small></div>', unsafe_allow_html=True)

    else:
        # 對話中
        st.markdown(f'<div class="info-card">📋 <b>題目</b><br><small>{st.session_state.socratic_question[:150]}{"..." if len(st.session_state.socratic_question) > 150 else ""}</small></div>', unsafe_allow_html=True)

        for role, msg in st.session_state.socratic_history:
            with st.chat_message("assistant" if role == "ai" else "user"):
                st.markdown(msg)

        user_input = st.chat_input("輸入你的想法、嘗試或疑問...")
        if user_input:
            st.session_state.socratic_history.append(("user", user_input))
            convo = f"題目：{st.session_state.socratic_question}\n\n對話歷程：\n"
            for role, msg in st.session_state.socratic_history:
                convo += f"\n【{'學生' if role == 'user' else '老師'}】{msg}\n"
            convo += "\n【請以老師身份繼續引導，每次只問 1 個問題】"
            reply = ask_ai(convo, system=st.session_state.socratic_system, engine=engine)
            st.session_state.socratic_history.append(("ai", reply))
            st.rerun()

        col_e1, col_e2 = st.columns([3, 1])
        with col_e1:
            if st.button("🔄 換一題", use_container_width=True):
                st.session_state.socratic_history = []
                st.session_state.socratic_question = ""
                st.rerun()
        with col_e2:
            if st.button("🏠 回首頁", use_container_width=True):
                st.session_state.socratic_history = []
                st.session_state.socratic_question = ""
                st.session_state.current_page = "🏠 首頁"
                if "page_radio" in st.session_state:
                    del st.session_state.page_radio
                st.rerun()


# ---------- 📓 錯題本 ----------
elif page == "📓 錯題本":
    st.header("📓 我的錯題本")

    tab1, tab2 = st.tabs(["📋 錯題清單", "🔁 智慧複習"])

    with tab1:
        filter_sub = st.selectbox("篩選科目", ["全部"] + ALL_SUBJECTS)
        show_reviewed = st.checkbox("顯示已複習")

        wrongs = get_wrongs(
            subject=None if filter_sub == "全部" else filter_sub,
            only_unreviewed=not show_reviewed,
        )

        if not wrongs:
            st.info("錯題本還是空的，到「刷題練習」累積錯題吧！")
        else:
            st.write(f"共 **{len(wrongs)}** 題")
            for w in wrongs:
                with st.expander(
                    f"#{w['id']} [{w['date']}] {w['subject']} — {w['topic']} "
                    f"{'✅ 已複習' if w['reviewed'] else '⏳ 待複習'}"
                ):
                    st.markdown(f"**題目**：\n\n{w['question']}")
                    st.markdown(f"**我的答案**：{w['my_answer']}")
                    st.markdown(f"**正確答案**：{w['correct_answer']}")
                    st.markdown(f"**錯誤原因**：{w['note']}")

                    cols = st.columns(2)
                    with cols[0]:
                        if not w["reviewed"]:
                            if st.button(f"✅ 標為已複習", key=f"rev_{w['id']}"):
                                mark_reviewed(w["id"])
                                st.rerun()
                    with cols[1]:
                        if st.button(f"🤖 請 AI 重新講解", key=f"explain_{w['id']}"):
                            with st.spinner("AI 講解中..."):
                                exp = ask_ai(
                                    f"請為高中生講解這題：\n\n{w['question']}\n\n"
                                    f"她當時答：{w['my_answer']}（錯）\n"
                                    f"正確答案：{w['correct_answer']}\n\n"
                                    f"請說明：1) 她錯在哪 2) 正確思路 3) 同類型題怎麼判斷",
                                    engine=engine,
                                )
                                st.markdown(exp)

    with tab2:
        st.subheader("🔁 依錯題本生成補強考卷")
        target_sub = st.selectbox("選擇科目", ALL_SUBJECTS, key="boost_sub")
        target_wrongs = get_wrongs(subject=target_sub, only_unreviewed=True)

        if not target_wrongs:
            st.info(f"{target_sub} 沒有未複習的錯題")
        else:
            st.write(f"📌 將依 {len(target_wrongs)} 題錯題分析弱點，生成 15 題補強練習")
            if st.button("🧨 生成補強卷", type="primary"):
                summary = "\n".join([
                    f"- 主題：{w['topic']}；題目：{w['question'][:100]}；錯因：{w['note']}"
                    for w in target_wrongs[:10]
                ])
                target_publisher = TEXTBOOK.get(target_sub, {}).get(grade, "通用版")
                prompt = f"""
以下是 {NICKNAME} 在 {target_sub} 的錯題紀錄。請：
1. 先用 3 句話分析她的核心弱點
2. 出 15 題「同觀念但不同情境」的補強練習
3. 由淺入深：5 題基礎、5 題中等、5 題進階
4. 每題後附詳解，特別點出「為什麼之前會錯」

【教材】{target_publisher}版 {grade}{target_sub}
【錯題】
{summary}
"""
                with st.spinner("AI 分析弱點中..."):
                    st.markdown(ask_ai(prompt, engine=engine))


# ---------- 📊 進度追蹤 ----------
elif page == "📊 進度追蹤":
    st.header("📊 學習進度追蹤")

    tab1, tab2, tab3 = st.tabs(["📈 分數趨勢", "📅 每日紀錄", "📊 月度報告"])

    with tab1:
        with st.expander("➕ 新增測驗分數"):
            with st.form("score_form"):
                s_sub = st.selectbox("科目", ALL_SUBJECTS)
                s_score = st.number_input("分數", 0, 100, 75)
                s_type = st.selectbox("測驗類型", ["學校段考", "模擬考", "AI 練習卷", "歷屆學測"])
                s_note = st.text_input("備註")
                if st.form_submit_button("儲存", type="primary"):
                    add_score(s_sub, s_score, s_type, s_note)
                    st.success("已記錄！")
                    st.rerun()

        st.subheader("各科最新成績")
        all_scores = get_scores()
        if all_scores:
            latest = {}
            for s in all_scores:
                if s["subject"] not in latest:
                    latest[s["subject"]] = s

            cols = st.columns(min(len(latest), 4))
            for i, (sub, entry) in enumerate(latest.items()):
                with cols[i % 4]:
                    delta_text = ""
                    sub_history = [s for s in all_scores if s["subject"] == sub]
                    if len(sub_history) >= 2:
                        delta = sub_history[0]["score"] - sub_history[1]["score"]
                        delta_text = f"{'+' if delta >= 0 else ''}{delta}"
                    st.metric(sub, f"{entry['score']} 分", delta_text)

            st.divider()
            st.subheader("完整紀錄")
            for s in all_scores[:20]:
                st.markdown(
                    f"- **{s['date']}** | {s['subject']} | "
                    f"**{s['score']}** 分 | {s['exam_type']} | {s['note']}"
                )
        else:
            st.info("還沒有分數紀錄")

    with tab2:
        st.subheader("📅 每日讀書紀錄")
        with get_db() as conn:
            recent = conn.execute(
                "SELECT date, SUM(questions_done) as qs, SUM(minutes_spent) as mins "
                "FROM daily_log WHERE date >= ? GROUP BY date ORDER BY date DESC",
                (str(date.today() - timedelta(days=14)),),
            ).fetchall()

        if recent:
            for r in recent:
                pct = min(int((r["qs"] or 0) / phase_info["daily_target"] * 100), 100)
                st.markdown(f"**{r['date']}** — {r['qs']} 題 / {r['mins']} 分鐘")
                st.markdown(f'<div class="progress-bar"><div class="progress-fill" style="width: {pct}%">{pct}%</div></div>', unsafe_allow_html=True)
        else:
            st.info("最近 14 天還沒有讀書紀錄。到「🏠 首頁」登錄今天的進度！")

    with tab3:
        st.subheader(f"📊 {date.today().strftime('%Y 年 %m 月')} 月度報告")
        month_stats = get_month_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("本月題數", f"{month_stats['questions']}")
        with col2:
            st.metric("本月時數", f"{month_stats['minutes'] // 60} 小時")
        with col3:
            st.metric("平均每天", f"{month_stats['questions'] // max(date.today().day, 1)} 題")
        
        if get_reward_enabled():
            st.divider()
            ach = get_achievement_status()
            st.subheader(f"🏆 達標進度：{ach['achieved_count']} / 4")
            for cond in ach["conditions"]:
                icon = "✅" if cond["achieved"] else "⏳"
                st.markdown(f"{icon} **{cond['name']}** — {cond['detail']}")
            
            if ach["is_great"]:
                st.success("🌟 滿分達標！本月你是月度學霸候選人！")
            elif ach["is_good"]:
                st.info("⭐ 月度標準達成！繼續加油！")
        else:
            st.caption("💡 達標獎勵系統目前未啟用")


# ---------- 🐱 我的貓咪 ----------
elif page == "🐱 我的貓咪":
    st.header("🐱 我的貓咪夥伴")
    st.caption("上傳貓咪照片，每次打開 App 都能看到牠陪你讀書 ❤️")

    cat_profile = get_cat_profile()

    with st.expander("✏️ 設定貓咪名字與個性", expanded=not cat_profile.get("cat_name")):
        with st.form("cat_profile_form"):
            cat_name = st.text_input("貓咪名字", value=cat_profile.get("cat_name", "小貓"))
            cat_personality = st.text_area(
                "貓咪個性描述",
                value=cat_profile.get("cat_personality", "可愛溫暖的貓咪"),
                placeholder="例如：很貪吃但很黏人的虎斑貓",
                height=80,
            )
            if st.form_submit_button("💾 儲存", type="primary"):
                save_cat_profile(cat_name, cat_personality)
                st.success("已儲存！")
                st.rerun()

    st.divider()

    builtin_photos = get_builtin_cat_photos()
    if builtin_photos:
        st.subheader(f"📂 GitHub 內建媒體（{len(builtin_photos)} 個）")
        st.caption("💡 這些檔案放在 GitHub 的 `cat_photos/` 資料夾，永久保存。")

        cols = st.columns(3)
        for i, p in enumerate(builtin_photos):
            with cols[i % 3]:
                if is_video(p):
                    st.video(str(p))
                    st.caption(f"🎬 {p.name}")
                else:
                    with open(p, "rb") as f:
                        st.image(f.read(), caption=f"📸 {p.name}", use_container_width=True)

        st.divider()

    st.subheader("📸 臨時上傳")
    uploaded = st.file_uploader(
        "選擇貓咪照片",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    if uploaded:
        for f in uploaded:
            photo_bytes = f.read()
            if len(photo_bytes) > 500_000:
                try:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(photo_bytes))
                    img.thumbnail((600, 600))
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    photo_bytes = buf.getvalue()
                except ImportError:
                    pass
            add_cat_photo(photo_bytes, f.name)
        st.success(f"✅ 已上傳 {len(uploaded)} 張照片！")
        st.rerun()

    photos = get_cat_photos()
    if photos:
        st.subheader(f"🖼️ 臨時上傳的照片（{len(photos)} 張）")
        cols = st.columns(3)
        for i, p in enumerate(photos):
            with cols[i % 3]:
                st.image(p["photo_data"], caption=p["caption"][:20], use_container_width=True)
                if st.button("🗑️ 刪除", key=f"del_{p['id']}"):
                    delete_cat_photo(p["id"])
                    st.rerun()


# ---------- 💰 費用監控（NT$ 為主）----------
elif page == "💰 費用監控":
    st.header("💰 API 費用監控")

    usage = get_usage_stats()
    monthly_limit_usd = float(st.secrets.get("MONTHLY_BUDGET_USD", "20"))
    monthly_limit_twd = monthly_limit_usd * USD_TO_TWD

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日花費", f"NT${usage['today_twd']:.0f}", help=f"≈ ${usage['today_usd']:.3f} USD")
    with col2:
        month_pct = min(usage["month_usd"] / monthly_limit_usd * 100, 100) if monthly_limit_usd else 0
        st.metric("本月花費", f"NT${usage['month_twd']:.0f}", f"預算 {month_pct:.0f}%")
    with col3:
        st.metric("今日呼叫", usage["today_calls"], "次")

    # 預算進度條（NT$ 顯示）
    bar_color = '#ef4444' if month_pct > 80 else '#f59e0b' if month_pct > 50 else '#10b981'
    st.markdown(f"""
    <div style="margin: 14px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px;">
            <span>本月預算 NT${monthly_limit_twd:.0f}</span>
            <span>{month_pct:.0f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width:{month_pct}%; background: {bar_color};">
                NT${usage['month_twd']:.0f}
            </div>
        </div>
        <div style="font-size:11px; color:#888; margin-top:3px;">
            計費週期：{date.today().replace(day=1)} ~ 月底｜匯率：1 USD = NT${USD_TO_TWD}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if month_pct > 80:
        st.warning("⚠️ 本月預算即將用完，請節省使用或請家長調整 Secrets 中的 MONTHLY_BUDGET_USD")

    st.divider()

    with get_db() as conn:
        engine_stats = conn.execute("""
            SELECT engine, COUNT(*) as calls, SUM(estimated_cost_usd) as cost,
                   SUM(input_tokens) as in_tk, SUM(output_tokens) as out_tk
            FROM api_usage
            WHERE date >= date('now', 'start of month')
            GROUP BY engine
        """).fetchall()

    if engine_stats:
        st.subheader("📊 本月各引擎使用統計")
        for s in engine_stats:
            cost_twd = (s['cost'] or 0) * USD_TO_TWD
            with st.expander(f"{s['engine']} — NT${cost_twd:.0f}（{s['calls']} 次）"):
                st.write(f"- 輸入 token：{s['in_tk']:,}")
                st.write(f"- 輸出 token：{s['out_tk']:,}")
                st.write(f"- 費用：NT${cost_twd:.1f} (≈ ${s['cost']:.4f} USD)")


# ---------- 💾 資料備份 ----------
elif page == "💾 資料備份":
    st.header("💾 資料備份")
    st.warning("⚠️ Streamlit Cloud 重啟可能會清空資料，建議**每週下載備份一次**。")

    backup_data = export_db_json()
    st.download_button(
        "⬇️ 下載完整備份（JSON）",
        backup_data,
        file_name=f"study_backup_{date.today()}.json",
        mime="application/json",
        type="primary",
    )

    with get_db() as conn:
        wrong_cnt = conn.execute("SELECT COUNT(*) FROM wrong_book").fetchone()[0]
        score_cnt = conn.execute("SELECT COUNT(*) FROM score_log").fetchone()[0]
        log_cnt = conn.execute("SELECT COUNT(*) FROM daily_log").fetchone()[0]

    st.markdown(f"""
    ### 📊 目前資料量
    - 錯題本：**{wrong_cnt}** 題
    - 分數紀錄：**{score_cnt}** 筆
    - 每日紀錄：**{log_cnt}** 筆
    """)

    st.divider()
    st.markdown("""
    ### 📱 把這個 App 加到 iPad 主畫面
    1. 在 iPad 用 **Safari** 打開這個網址
    2. 點底部的 **分享** 按鈕（方框 + 向上箭頭）
    3. 選 **「加入主畫面」**
    """)


# ---------- 🔐 家長後台 ----------
elif page == "🔐 家長後台":
    st.header("🔐 家長後台")

    if not check_parent_password():
        st.stop()

    col_header, col_logout = st.columns([5, 1])
    with col_header:
        st.success("✅ 已登入家長後台")
    with col_logout:
        if st.button("登出"):
            st.session_state.parent_authenticated = False
            st.rerun()

    st.divider()

    # ── 📊 Queenie 學習儀表板 ──
    st.subheader(f"📊 {STUDENT_NAME} 學習儀表板")
    st.caption(f"計費週期：{date.today().replace(day=1)} ~ 月底 | 今天：{date.today()}")

    # 4 大關鍵指標
    month_stats = get_month_stats()
    streak = get_streak_days(phase_info["daily_target"])
    usage_stats = get_usage_stats()
    all_scores = get_scores()

    avg_score = 0
    if all_scores:
        recent_scores = [s["score"] for s in all_scores[:20]]
        avg_score = round(sum(recent_scores) / len(recent_scores))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div style="background:white; border:1px solid #d6d6d8; border-radius:6px; padding:14px; border-left:3px solid #1e3a5f;">
            <div style="font-size:11px; color:#6b7280;">🔥 連續達標</div>
            <div style="font-size:28px; font-weight:600; color:#1e3a5f;">{streak}</div>
            <div style="font-size:11px; color:#6b7280;">天</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:white; border:1px solid #d6d6d8; border-radius:6px; padding:14px; border-left:3px solid #4a7c59;">
            <div style="font-size:11px; color:#6b7280;">📝 本月題數</div>
            <div style="font-size:28px; font-weight:600; color:#4a7c59;">{month_stats['questions']}</div>
            <div style="font-size:11px; color:#6b7280;">題</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background:white; border:1px solid #d6d6d8; border-radius:6px; padding:14px; border-left:3px solid #c08827;">
            <div style="font-size:11px; color:#6b7280;">⭐ 平均分數</div>
            <div style="font-size:28px; font-weight:600; color:#c08827;">{avg_score}</div>
            <div style="font-size:11px; color:#6b7280;">分（最近 20 次）</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div style="background:white; border:1px solid #d6d6d8; border-radius:6px; padding:14px; border-left:3px solid #d97757;">
            <div style="font-size:11px; color:#6b7280;">⏰ 本月時數</div>
            <div style="font-size:28px; font-weight:600; color:#d97757;">{month_stats['minutes'] // 60}</div>
            <div style="font-size:11px; color:#6b7280;">小時</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 各科平均分數 + 進度條
    st.markdown("**各科平均分數**")
    if all_scores:
        subject_scores = {}
        for s in all_scores:
            sub = s["subject"]
            if sub not in subject_scores:
                subject_scores[sub] = []
            subject_scores[sub].append(s["score"])

        for sub, scores in sorted(subject_scores.items()):
            avg = round(sum(scores) / len(scores))
            pct = avg
            bar_color = "#4a7c59" if avg >= 80 else "#c08827" if avg >= 60 else "#b94040"
            col_sub1, col_sub2 = st.columns([1, 3])
            with col_sub1:
                st.caption(f"{sub}（{len(scores)} 次）")
            with col_sub2:
                st.markdown(f"""
                <div style="margin-top:4px;">
                    <div style="background:#e5e7eb; border-radius:99px; height:6px; position:relative;">
                        <div style="width:{pct}%; background:{bar_color}; height:100%; border-radius:99px;"></div>
                    </div>
                    <div style="font-size:11px; color:{bar_color}; text-align:right; margin-top:1px;">{avg} 分</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("尚無分數記錄，讓 Queenie 完成幾次練習後再來看！")

    st.divider()

    # 最近練習記錄
    st.markdown("**最近練習記錄**")
    if all_scores:
        recent = all_scores[:10]
        score_data = []
        for s in recent:
            score_emoji = "🌟" if s["score"] >= 80 else "💪" if s["score"] >= 60 else "📚"
            score_data.append(f"| {s['date']} | {s['subject']} | {score_emoji} **{s['score']}** 分 | {s['exam_type']} | {s['note']} |")

        st.markdown("| 日期 | 科目 | 分數 | 類型 | 備註 |")
        st.markdown("|------|------|------|------|------|")
        for row in score_data:
            st.markdown(row)
    else:
        st.caption("尚無記錄")

    st.divider()

    # 本月 API 費用
    st.markdown("**本月費用**")
    monthly_limit_usd = float(st.secrets.get("MONTHLY_BUDGET_USD", "20"))
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("今日", f"NT${usage_stats['today_twd']:.0f}")
    with col_c2:
        st.metric("本月", f"NT${usage_stats['month_twd']:.0f}", f"預算 NT${monthly_limit_usd*32:.0f}")
    with col_c3:
        st.metric("今日呼叫", f"{usage_stats['today_calls']} 次")

    st.divider()

    # 模組開關
    st.subheader("⚙️ 功能設定")
    
    reward_on = st.toggle(
        "🏆 達標獎勵系統",
        value=get_reward_enabled(),
        help="開啟後，Queenie 會在「🏠 首頁」和「進度追蹤」看到達標進度。獎勵內容由您決定，App 不顯示具體獎品。",
    )
    if reward_on != get_reward_enabled():
        set_setting("reward_enabled", "1" if reward_on else "0")
        st.rerun()
    
    if reward_on:
        st.info("✅ 獎勵系統已啟用")
    else:
        st.caption("💡 建議：使用 App 持續 2-3 週後再啟動獎勵系統，效果更好")
    
    st.divider()
    
    # 達標標準設定
    if reward_on:
        st.subheader("🎯 達標標準設定")
        
        with st.form("reward_settings"):
            month_q_target = st.number_input(
                "每月題數目標",
                min_value=100, max_value=2000, step=50,
                value=int(get_setting("monthly_q_target", "600")),
                help="每月完成多少題視為達標"
            )
            
            st.markdown("**🎯 條件 2：學校成績進步（您手動標記）**")
            school_improved = st.checkbox(
                "本月學校成績有 1+ 科進步 5 分以上",
                value=get_setting("month_school_improved", "0") == "1",
            )
            
            st.markdown("**🎯 條件 4：心態評估（您主觀評估）**")
            attitude_ok = st.checkbox(
                "本月 Queenie 心態狀態良好",
                value=get_setting("month_attitude_ok", "0") == "1",
            )
            
            if st.form_submit_button("💾 儲存設定", type="primary"):
                set_setting("monthly_q_target", str(month_q_target))
                set_setting("month_school_improved", "1" if school_improved else "0")
                set_setting("month_attitude_ok", "1" if attitude_ok else "0")
                st.success("✅ 已儲存")
                st.rerun()
        
        st.divider()
        
        # 當前狀態
        st.subheader("📊 當前達標狀態")
        ach = get_achievement_status()
        for cond in ach["conditions"]:
            icon = "✅" if cond["achieved"] else "⏳"
            st.markdown(f"{icon} **{cond['name']}** — {cond['detail']}")
        
        st.markdown(f"### 進度：{ach['achieved_count']} / 4")
        if ach["is_great"]:
            st.success("🌟 Queenie 本月滿分達標！可以準備驚喜獎勵 ❤️")
        elif ach["is_good"]:
            st.info("⭐ Queenie 本月達成標準！可以給予肯定")
    
    st.divider()
    
    # 家長觀察筆記
    st.subheader("📝 家長觀察筆記")
    notes = st.text_area(
        "私下記錄（Queenie 看不到）",
        value=get_setting("parent_notes", ""),
        height=120,
        placeholder="記錄 Queenie 的觀察、與爸爸的討論、給 AI 的指示..."
    )
    if st.button("💾 儲存筆記"):
        set_setting("parent_notes", notes)
        st.success("✅ 筆記已儲存")
    
    st.divider()
    
    # 重要提醒
    with st.expander("📖 家長使用指南"):
        st.markdown("""
        ### 🎯 漸進式啟動策略（建議）
        
        **第 1-2 週**：獎勵系統「關閉」
        - 讓 Queenie 自然培養使用習慣
        - 您私下觀察她的接受度
        
        **第 3 週**：評估
        - 她使用頻率夠高嗎？
        - 學校成績有變化嗎？
        - 跟爸爸討論獎勵內容
        
        **第 4 週起**：啟動獎勵系統
        - 找輕鬆時刻告訴 Queenie：「媽媽看你最近用 App 很認真，多了個達標功能」
        - 不要事先承諾具體獎勵內容（保留驚喜）
        
        ### 💝 月底家庭會議模板
        
        1. **先稱讚**：「化學進步好多！」
        2. **問感覺**：「用 App 順手嗎？」
        3. **給驚喜**：「媽媽決定給你 X 獎勵」
        4. **問目標**：「下個月想突破哪科？」
        
        ### 🛡️ 鐵則
        
        - ❌ 不要說「達標就給 NT$3000」（變成交易）
        - ✅ 要說「我看到你的努力，準備了驚喜」（變成肯定）
        """)


# 頁尾
st.divider()
st.caption(f"🎓 v3.8 | {engine} | {publisher}版 {grade}{subject} | 距學測 {phase_info['days_left']} 天")
