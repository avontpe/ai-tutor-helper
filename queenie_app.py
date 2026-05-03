"""
AI Tutor Helper v3.5
================================
跨裝置雲端網頁 App（iPad / 桌機 / 手機皆可用）

核心功能：
- 🤖 雙 AI 引擎切換（Claude / Gemini）
- 📅 每日任務面板
- 📝 段考刷題 + 蘇格拉底引導
- 🔁 智慧錯題本（SQLite 持久化）
- 📊 分數趨勢追蹤
- 🎯 學測倒數 + 階段進度條
- 📱 PWA 支援
- 🔒 個人資料分離設計（個資存 Secrets，程式碼通用化）
"""

import streamlit as st
import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from contextlib import contextmanager

# ============================================================
# 0. 個人化設定（從 Secrets 讀取，不寫死在程式碼）
# ============================================================

def get_user_config():
    """從 Streamlit Secrets 讀取個人化設定，全部都有預設值。"""
    return {
        "STUDENT_NAME": st.secrets.get("STUDENT_NAME", "同學"),
        "SCHOOL_NAME": st.secrets.get("SCHOOL_NAME", ""),
        "EXAM_YEAR": st.secrets.get("EXAM_YEAR", "116"),
        "EXAM_DATE_STR": st.secrets.get("EXAM_DATE", "2027-01-22"),
        "DEFAULT_GRADE": st.secrets.get("DEFAULT_GRADE", "高二"),
        "TEXTBOOK_JSON": st.secrets.get("TEXTBOOK_JSON", ""),
    }

USER = get_user_config()
STUDENT_NAME = USER["STUDENT_NAME"]
SCHOOL_NAME = USER["SCHOOL_NAME"]
EXAM_YEAR = USER["EXAM_YEAR"]

# 解析考試日期
try:
    EXAM_DATE = datetime.strptime(USER["EXAM_DATE_STR"], "%Y-%m-%d").date()
except:
    EXAM_DATE = date(2027, 1, 22)

START_DATE = date(2026, 5, 2)

# 學生暱稱（個人化但對外通用）
NICKNAME = f"Hi {STUDENT_NAME[:1]}~"


# ============================================================
# 1. 應用程式設定
# ============================================================

st.set_page_config(
    page_title=f"{NICKNAME} 學測導航",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---- 預設教科書版本（如果 Secrets 沒設定就用這個通用版）----
DEFAULT_TEXTBOOK = {
    "國文": {"高二": "通用版", "高三": "通用版"},
    "英文": {"高二": "通用版", "高三": "通用版"},
    "數學": {"高二": "通用版", "高三": "通用版"},
    "物理": {"高二": "通用版", "高三": "通用版"},
    "化學": {"高二": "通用版", "高三": "通用版"},
    "生物": {"高二": "通用版", "高三": "通用版"},
    "歷史": {"高二": "通用版", "高三": "通用版"},
    "地理": {"高二": "通用版", "高三": "通用版"},
    "公民": {"高二": "通用版", "高三": "通用版"},
}

# 從 Secrets 讀取真正的版本對應（如果有設定）
try:
    if USER["TEXTBOOK_JSON"]:
        TEXTBOOK = json.loads(USER["TEXTBOOK_JSON"])
    else:
        TEXTBOOK = DEFAULT_TEXTBOOK
except:
    TEXTBOOK = DEFAULT_TEXTBOOK

SUBJECTS = list(TEXTBOOK.keys())

# ---- SQLite 資料庫位置 ----
DB_PATH = Path("study_data.db")


# ============================================================
# 2. 響應式 CSS
# ============================================================

st.markdown("""
<style>
    :root {
        --primary: #004a99;
        --primary-light: #1976d2;
        --accent: #ff6b35;
        --bg-card: #f8fafc;
    }

    .stButton > button {
        background-color: var(--primary);
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: var(--primary-light);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,74,153,0.3);
    }
    .stButton > button[kind="primary"] {
        background-color: var(--accent);
    }

    @media (min-width: 768px) and (max-width: 1024px) {
        .stMarkdown { font-size: 17px; }
        .stButton > button { padding: 0.8rem 1.4rem; font-size: 16px; }
        h1 { font-size: 28px !important; }
        h2 { font-size: 22px !important; }
    }

    @media (max-width: 768px) {
        .stMarkdown { font-size: 16px; }
        .block-container { padding: 1rem 0.5rem !important; }
    }

    .progress-bar {
        background: #e0e7ff;
        border-radius: 12px;
        height: 24px;
        overflow: hidden;
        margin: 8px 0;
    }
    .progress-fill {
        background: linear-gradient(90deg, #004a99, #1976d2);
        height: 100%;
        border-radius: 12px;
        transition: width 0.5s;
        text-align: right;
        color: white;
        font-weight: bold;
        padding-right: 8px;
        line-height: 24px;
        font-size: 13px;
    }

    .info-card {
        background: var(--bg-card);
        border-left: 4px solid var(--primary);
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
    }

    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>

<link rel="apple-touch-icon" href="https://emojicdn.elk.sh/🎓?style=apple">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
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
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT,
            question TEXT NOT NULL,
            my_answer TEXT,
            correct_answer TEXT,
            note TEXT,
            reviewed INTEGER DEFAULT 0,
            review_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS score_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            score INTEGER NOT NULL,
            exam_type TEXT,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            subject TEXT,
            questions_done INTEGER DEFAULT 0,
            minutes_spent INTEGER DEFAULT 0,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS cat_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploaded_at TEXT NOT NULL,
            photo_data BLOB NOT NULL,
            caption TEXT
        );

        CREATE TABLE IF NOT EXISTS cat_profile (
            id INTEGER PRIMARY KEY,
            cat_name TEXT,
            cat_personality TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            engine TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0
        );
        """)


def add_wrong(subject, topic, question, my_ans, correct_ans, note):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO wrong_book (date, subject, topic, question, my_answer, correct_answer, note) VALUES (?,?,?,?,?,?,?)",
            (str(date.today()), subject, topic, question, my_ans, correct_ans, note),
        )


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
        conn.execute(
            "UPDATE wrong_book SET reviewed=1, review_count=review_count+1 WHERE id=?",
            (wrong_id,),
        )


def add_score(subject, score, exam_type, note):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO score_log (date, subject, score, exam_type, note) VALUES (?,?,?,?,?)",
            (str(date.today()), subject, score, exam_type, note),
        )


def get_scores(subject=None):
    with get_db() as conn:
        if subject:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM score_log WHERE subject=? ORDER BY date DESC", (subject,)
            ).fetchall()]
        return [dict(r) for r in conn.execute(
            "SELECT * FROM score_log ORDER BY date DESC"
        ).fetchall()]


def log_daily(subject, q_count, minutes, note=""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO daily_log (date, subject, questions_done, minutes_spent, note) VALUES (?,?,?,?,?)",
            (str(date.today()), subject, q_count, minutes, note),
        )


def get_today_done():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT subject, SUM(questions_done) as qs, SUM(minutes_spent) as mins FROM daily_log WHERE date=? GROUP BY subject",
            (str(date.today()),),
        ).fetchall()
        return [dict(r) for r in rows]


def export_db_json():
    data = {}
    with get_db() as conn:
        for table in ["wrong_book", "score_log", "daily_log", "cat_profile"]:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(r) for r in rows]
    return json.dumps(data, ensure_ascii=False, indent=2)


def add_cat_photo(photo_bytes, caption=""):
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM cat_photos").fetchone()[0]
        if count >= 6:
            conn.execute("DELETE FROM cat_photos WHERE id = (SELECT MIN(id) FROM cat_photos)")
        conn.execute(
            "INSERT INTO cat_photos (uploaded_at, photo_data, caption) VALUES (?,?,?)",
            (str(datetime.now()), photo_bytes, caption),
        )


def get_cat_photos():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM cat_photos ORDER BY id DESC"
        ).fetchall()]


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
            (name, personality, str(datetime.now())),
        )


def get_streak_days():
    target = get_phase()["daily_target"]
    with get_db() as conn:
        rows = conn.execute("""
            SELECT date, SUM(questions_done) as total
            FROM daily_log
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """).fetchall()
    streak = 0
    today = date.today()
    for r in rows:
        row_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
        if row_date == today - timedelta(days=streak) and (r["total"] or 0) >= target:
            streak += 1
        else:
            break
    return streak


PRICING = {
    "Claude": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "Gemini": {"input": 1.25 / 1_000_000, "output": 5.0 / 1_000_000},
}


def log_api_usage(engine, input_tokens, output_tokens):
    cost = (input_tokens * PRICING[engine]["input"] +
            output_tokens * PRICING[engine]["output"])
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_usage (date, engine, input_tokens, output_tokens, estimated_cost_usd) VALUES (?,?,?,?,?)",
            (str(date.today()), engine, input_tokens, output_tokens, cost),
        )
    return cost


def get_usage_stats():
    with get_db() as conn:
        today_cost = conn.execute(
            "SELECT SUM(estimated_cost_usd) FROM api_usage WHERE date=?",
            (str(date.today()),),
        ).fetchone()[0] or 0
        month_start = date.today().replace(day=1)
        month_cost = conn.execute(
            "SELECT SUM(estimated_cost_usd) FROM api_usage WHERE date>=?",
            (str(month_start),),
        ).fetchone()[0] or 0
        today_calls = conn.execute(
            "SELECT COUNT(*) FROM api_usage WHERE date=?",
            (str(date.today()),),
        ).fetchone()[0]
    return {"today_usd": today_cost, "month_usd": month_cost, "today_calls": today_calls}


init_db()


# ============================================================
# 4. 學習階段判定
# ============================================================

def get_phase(today=None):
    if today is None:
        today = date.today()
    days_left = max((EXAM_DATE - today).days, 0)
    days_passed = max((today - START_DATE).days, 0)
    total_days = (EXAM_DATE - START_DATE).days
    progress_pct = min(int(days_passed / total_days * 100), 100)

    if today < date(2026, 7, 1):
        phase = "Phase 1：補洞期"
        focus = "跟學校段考 + 補基礎弱點"
        daily_target = 15
        emoji = "🌱"
    elif today < date(2026, 10, 1):
        phase = "Phase 2：暑假黃金期"
        focus = "全範圍重新梳理（決勝負的 3 個月）"
        daily_target = 35
        emoji = "🔥"
    elif today < date(2026, 12, 25):
        phase = "Phase 3：模考衝刺"
        focus = "歷屆學測題 + 計時訓練"
        daily_target = 50
        emoji = "⚡"
    else:
        phase = "Phase 4：考前精修"
        focus = "只回顧錯題本、保持作息"
        daily_target = 20
        emoji = "🎯"

    return {
        "phase": phase, "focus": focus, "daily_target": daily_target,
        "days_left": days_left, "progress_pct": progress_pct, "emoji": emoji,
    }


# ============================================================
# 5. AI 引擎抽象層
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
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-pro")
    except ImportError:
        return None


def ask_ai(prompt, system="", engine="Gemini"):
    """統一 AI 介面，含 token 計算與費用記錄。"""
    default_system = f"你是一位資深的台灣高中升大學家教老師，熟悉 108 課綱與大學學測歷屆題型。學生暱稱「{NICKNAME}」。回答用繁體中文。"
    system = system or default_system

    usage = get_usage_stats()
    monthly_limit = float(st.secrets.get("MONTHLY_BUDGET_USD", "30"))
    if usage["month_usd"] >= monthly_limit:
        return f"⚠️ 已達本月 API 預算上限 ${monthly_limit} USD（目前 ${usage['month_usd']:.2f}）。請等下個月或調整預算。"

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
            import google.generativeai as genai
            model_with_sys = genai.GenerativeModel(
                "gemini-1.5-pro", system_instruction=system
            )
            response = model_with_sys.generate_content(prompt)
            try:
                in_tokens = response.usage_metadata.prompt_token_count
                out_tokens = response.usage_metadata.candidates_token_count
            except:
                in_tokens = len(prompt) // 3
                out_tokens = len(response.text) // 3
            log_api_usage("Gemini", in_tokens, out_tokens)
            return response.text
        except Exception as e:
            return f"❌ Gemini 錯誤：{type(e).__name__} — {str(e)}"


# ============================================================
# 6. 側邊欄
# ============================================================

import random
import base64
import os

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


with st.sidebar:
    cat_profile = get_cat_profile()
    cat_photos = get_cat_photos()
    builtin_photos = get_builtin_cat_photos()
    streak = get_streak_days()

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
            if is_video(chosen):
                media_type = "video"
                media_mime = get_media_mime(chosen)
            else:
                media_type = "image"
                media_mime = get_media_mime(chosen)
        else:
            photo_b64 = base64.b64encode(chosen["photo_data"]).decode()
            media_type = "image"
            media_mime = "image/jpeg"

    if photo_b64:
        today_done = sum(t["qs"] or 0 for t in get_today_done())
        target = get_phase()["daily_target"]
        cat_name = cat_profile["cat_name"]
        if today_done >= target:
            cat_mood = "😻"
            cat_says = f"{NICKNAME} 今天好棒！已完成 {today_done} 題了～"
        elif today_done >= target * 0.5:
            cat_says = f"喵～繼續加油！還差 {target - today_done} 題就達標！"
            cat_mood = "🐱"
        elif today_done > 0:
            cat_says = f"喵嗚～你已做了 {today_done} 題，再 push 一下！"
            cat_mood = "😺"
        else:
            cat_says = f"主人～今天還沒開始念書喔，{cat_name} 在等你！"
            cat_mood = "😿"

        total_count = len(all_options)
        photo_count_hint = f"📸 收藏了 {total_count} 個影像" if total_count > 1 else ""

        # 注意：HTML 內容必須緊靠左側無縮排，否則 Streamlit 會誤判為程式碼區塊
        if media_type == "video":
            media_html = f'<video autoplay loop muted playsinline style="width:120px; height:120px; object-fit:cover; border-radius:50%; border:3px solid #ff6b35; box-shadow:0 4px 12px rgba(0,0,0,0.15);"><source src="data:{media_mime};base64,{photo_b64}" type="{media_mime}"></video>'
        else:
            media_html = f'<img src="data:{media_mime};base64,{photo_b64}" style="width:120px; height:120px; object-fit:cover; border-radius:50%; border:3px solid #ff6b35; box-shadow:0 4px 12px rgba(0,0,0,0.15);">'

        streak_html = f'<div style="margin-top:6px; font-size:12px; color:#ff6b35; font-weight:bold;">🔥 連續達標 {streak} 天！</div>' if streak > 0 else ''
        count_html = f'<div style="margin-top:4px; font-size:11px; color:#8d6e63;">{photo_count_hint}</div>' if photo_count_hint else ''

        sidebar_html = (
            f'<div style="text-align:center; padding:10px; background:linear-gradient(135deg,#fff3e0,#ffe0b2); border-radius:12px; margin-bottom:12px;">'
            f'{media_html}'
            f'<div style="margin-top:8px; font-weight:bold; color:#d84315;">{cat_mood} {cat_name}</div>'
            f'<div style="font-size:13px; color:#5d4037; margin-top:4px; padding:0 8px;">"{cat_says}"</div>'
            f'{streak_html}'
            f'{count_html}'
            f'</div>'
        )
        st.markdown(sidebar_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center; padding:20px; background:#fff3e0; border-radius:12px; margin-bottom:12px;">'
            '<div style="font-size:40px;">🐱</div>'
            '<div style="font-size:13px; color:#5d4037; margin-top:8px;">'
            '到「🐱 我的貓咪」上傳照片！'
            '</div></div>',
            unsafe_allow_html=True
        )

    st.title(f"🎓 {NICKNAME} 學測導航")

    engine = st.radio(
        "🤖 AI 引擎",
        ["Gemini", "Claude"],
        help="Claude：題目品質高（貴 3x）；Gemini：免費額度大、速度快",
        horizontal=True,
    )

    usage = get_usage_stats()
    if usage["today_calls"] > 0:
        st.caption(f"📊 今日 {usage['today_calls']} 次 / ${usage['today_usd']:.3f} | 本月 ${usage['month_usd']:.2f}")

    st.divider()

    grade = st.selectbox("年級", ["高二", "高三"], index=0 if USER["DEFAULT_GRADE"] == "高二" else 1)
    subject = st.selectbox("科目", SUBJECTS)
    publisher = TEXTBOOK[subject][grade]

    school_label = f"{SCHOOL_NAME} " if SCHOOL_NAME else ""
    st.markdown(f"""
    <div class="info-card">
    📚 {school_label}<b>{publisher}版</b> {grade}{subject}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "功能選單",
        ["🏠 今日任務", "📝 刷題練習", "🧠 蘇格拉底引導",
         "📓 錯題本", "📊 進度追蹤", "🐱 我的貓咪",
         "💰 費用監控", "💾 資料備份"],
    )


# ============================================================
# 7. 頂部資訊欄
# ============================================================

phase_info = get_phase()

st.markdown(f"""
<div style="background: linear-gradient(135deg, #004a99, #1976d2); color: white; padding: 16px 20px; border-radius: 12px; margin-bottom: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div style="font-size: 14px; opacity: 0.85;">距離 {EXAM_YEAR} 學測</div>
            <div style="font-size: 32px; font-weight: bold;">{phase_info['days_left']} 天</div>
        </div>
        <div>
            <div style="font-size: 14px; opacity: 0.85;">{phase_info['emoji']} 目前階段</div>
            <div style="font-size: 18px; font-weight: 600;">{phase_info['phase']}</div>
        </div>
        <div>
            <div style="font-size: 14px; opacity: 0.85;">每日目標</div>
            <div style="font-size: 18px; font-weight: 600;">{phase_info['daily_target']} 題</div>
        </div>
    </div>
    <div style="margin-top: 12px;">
        <div class="progress-bar" style="background: rgba(255,255,255,0.2);">
            <div class="progress-fill" style="width: {phase_info['progress_pct']}%; background: linear-gradient(90deg, #ff6b35, #ffa726);">
                {phase_info['progress_pct']}%
            </div>
        </div>
        <div style="font-size: 13px; opacity: 0.85; margin-top: 4px;">📌 {phase_info['focus']}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# 8. 頁面分流
# ============================================================

if page == "🏠 今日任務":
    st.header(f"🏠 {NICKNAME}，今天該做什麼？")

    today_done = get_today_done()
    total_done = sum(t["qs"] or 0 for t in today_done)
    total_mins = sum(t["mins"] or 0 for t in today_done)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日已完成題數", f"{total_done} 題", f"目標 {phase_info['daily_target']} 題")
    with col2:
        st.metric("今日讀書時間", f"{total_mins} 分", f"≈ {total_mins // 60} 小時 {total_mins % 60} 分")
    with col3:
        completion = min(int(total_done / phase_info['daily_target'] * 100), 100) if phase_info['daily_target'] else 0
        st.metric("今日完成度", f"{completion}%", "💪 加油！" if completion < 100 else "✅ 達標！")

    st.divider()

    st.subheader("📋 今日建議分配")
    weakness_subjects = []
    with get_db() as conn:
        for s in SUBJECTS:
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
        st.info("👍 目前沒有累積錯題，繼續到「刷題練習」累積基礎吧！")

    st.divider()
    st.subheader("✏️ 登錄今日進度")
    with st.form("daily_log_form"):
        log_subject = st.selectbox("科目", SUBJECTS, key="log_sub")
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


elif page == "📝 刷題練習":
    st.header(f"📝 {publisher}版 {grade}{subject} — 刷題練習")

    last_scores = get_scores(subject)
    boost_hint = ""
    if last_scores and last_scores[0]["score"] < 80:
        last = last_scores[0]
        boost_hint = f"（{NICKNAME} 上次 {subject} 得分為 {last['score']} 分。請出修正與強化版題目，幫她從 {last['score']} 進步到 80+。）"
        st.warning(f"📈 偵測到上次 {subject} 得 {last['score']} 分，已開啟「進步衝刺模式」")

    col1, col2 = st.columns([2, 1])
    with col1:
        chapter = st.text_input(
            "本次範圍 / 章節",
            placeholder="例如：第三章 三角函數和角公式 / Unit 4 Reading"
        )
    with col2:
        difficulty = st.selectbox("難度", ["基礎", "中等", "進階", "挑戰學測"])

    col3, col4 = st.columns(2)
    with col3:
        num_q = st.slider("題數", 5, 30, 10 if subject == "數學" else 15)
    with col4:
        include_essay = st.checkbox("含非選擇題（計算/申論）", value=True)

    if st.button("🚀 生成練習題", type="primary"):
        if not chapter.strip():
            st.warning("請先輸入章節範圍")
        else:
            extra = "請務必包含選填題與計算題。" if subject == "數學" and include_essay else ""
            extra += "請包含至少 3 題非選擇題。" if include_essay and subject != "數學" else ""

            prompt = f"""
請幫高中生 {NICKNAME} 出 {num_q} 題 **{subject}** 練習題。{boost_hint}

【教材】{publisher}版 {grade}{subject}
【範圍】{chapter}
【難度】{difficulty}
【格式】
1. 題型混合：選擇題 + 非選擇題。{extra}
2. 仿照大學學測 108 課綱題型（情境化、跨領域）
3. 全部題目先列出，編號 1, 2, 3...
4. 用「---詳解---」分隔，再給每題詳解
5. 詳解要包含：解題思路、易錯點、相關觀念連結
6. 不要先給答案，讓她答完再對
"""
            with st.spinner(f"{engine} 正在出題中..."):
                result = ask_ai(prompt, engine=engine)
                st.session_state.last_quiz = result
                st.session_state.last_subject = subject
                st.session_state.last_topic = chapter

    if "last_quiz" in st.session_state:
        st.divider()
        st.markdown(st.session_state.last_quiz)

        st.divider()
        with st.expander("✏️ 把答錯的題目加入錯題本"):
            with st.form("add_wrong_form"):
                w_q = st.text_area("題目", height=100)
                w_my = st.text_input("我的答案")
                w_correct = st.text_input("正確答案")
                w_note = st.text_input("錯誤原因", placeholder="觀念混淆？粗心？不會？")
                if st.form_submit_button("📌 加入錯題本"):
                    if w_q.strip():
                        add_wrong(
                            st.session_state.last_subject,
                            st.session_state.last_topic,
                            w_q, w_my, w_correct, w_note
                        )
                        st.success("✅ 已加入錯題本！")


elif page == "🧠 蘇格拉底引導":
    st.header("🧠 蘇格拉底解題引導")
    st.caption("📌 不直接給答案，AI 會用追問方式帶你自己想出來。")

    if "socratic_history" not in st.session_state:
        st.session_state.socratic_history = []
        st.session_state.socratic_question = ""

    if not st.session_state.socratic_history:
        question = st.text_area(
            "貼上你卡住的題目",
            placeholder="完整題目越詳細越好",
            height=180,
        )
        if st.button("🎯 開始引導", type="primary") and question.strip():
            st.session_state.socratic_question = question
            system_prompt = f"""你是一位耐心的家教老師 Tutor，用蘇格拉底引導法幫 {NICKNAME} 解 {subject} 題目。

【鐵律】
1. 絕對不可以直接給答案
2. 用「提問」引導她思考，每次只問 1-2 個關鍵問題
3. 從她的回答判斷她卡在哪一步
4. 答對中間步驟就肯定她、繼續引導下一步
5. 答錯不要直接糾正，反問「你為什麼這樣想？」或提示她檢查某個條件
6. 語氣溫和像鄰家姊姊，但保持專業
7. 最後她算出答案時，幫她回顧整題的關鍵觀念
"""
            first = ask_ai(
                f"題目如下：\n\n{question}\n\n請開始你的第一個引導問題。",
                system=system_prompt, engine=engine,
            )
            st.session_state.socratic_history.append(("ai", first))
            st.session_state.socratic_system = system_prompt
            st.rerun()
    else:
        st.markdown(f"""
        <div class="info-card">
        📋 <b>題目</b><br>{st.session_state.socratic_question}
        </div>
        """, unsafe_allow_html=True)

        for role, msg in st.session_state.socratic_history:
            with st.chat_message("assistant" if role == "ai" else "user"):
                st.markdown(msg)

        user_input = st.chat_input("輸入你的想法 / 嘗試...")
        if user_input:
            st.session_state.socratic_history.append(("user", user_input))
            convo = f"題目：{st.session_state.socratic_question}\n\n對話歷程：\n"
            for role, msg in st.session_state.socratic_history:
                convo += f"\n【{'學生' if role == 'user' else '老師'}】{msg}\n"
            convo += "\n【請以老師身份繼續引導】"
            reply = ask_ai(convo, system=st.session_state.socratic_system, engine=engine)
            st.session_state.socratic_history.append(("ai", reply))
            st.rerun()

        if st.button("🔄 換一題"):
            st.session_state.socratic_history = []
            st.session_state.socratic_question = ""
            st.rerun()


elif page == "📓 錯題本":
    st.header("📓 我的錯題本")

    tab1, tab2 = st.tabs(["📋 錯題清單", "🔁 智慧複習"])

    with tab1:
        filter_sub = st.selectbox("篩選科目", ["全部"] + SUBJECTS)
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
        target_sub = st.selectbox("選擇科目", SUBJECTS, key="boost_sub")
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
                prompt = f"""
以下是 {NICKNAME} 在 {target_sub} 的錯題紀錄。請：
1. 先用 3 句話分析她的核心弱點
2. 出 15 題「同觀念但不同情境」的補強練習
3. 由淺入深：5 題基礎、5 題中等、5 題進階
4. 每題後附詳解，特別點出「為什麼之前會錯」

【教材】{TEXTBOOK[target_sub][grade]}版 {grade}{target_sub}
【錯題】
{summary}
"""
                with st.spinner("AI 分析弱點中..."):
                    st.markdown(ask_ai(prompt, engine=engine))


elif page == "📊 進度追蹤":
    st.header("📊 學習進度追蹤")

    tab1, tab2 = st.tabs(["📈 分數趨勢", "📅 每日紀錄"])

    with tab1:
        with st.expander("➕ 新增測驗分數"):
            with st.form("score_form"):
                s_sub = st.selectbox("科目", SUBJECTS)
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
                st.markdown(f"""
                **{r['date']}** — {r['qs']} 題 / {r['mins']} 分鐘
                <div class="progress-bar"><div class="progress-fill" style="width: {pct}%">{pct}%</div></div>
                """, unsafe_allow_html=True)
        else:
            st.info("最近 14 天還沒有讀書紀錄。到「今日任務」登錄今天的進度！")


elif page == "🐱 我的貓咪":
    st.header("🐱 我的貓咪夥伴")
    st.caption("上傳貓咪照片或影片，每次打開 App 都能看到牠陪你讀書 ❤️")

    cat_profile = get_cat_profile()

    with st.expander("✏️ 設定貓咪名字與個性", expanded=not cat_profile.get("cat_name")):
        with st.form("cat_profile_form"):
            cat_name = st.text_input(
                "貓咪名字",
                value=cat_profile.get("cat_name", "小貓"),
            )
            cat_personality = st.text_area(
                "貓咪個性描述",
                value=cat_profile.get("cat_personality", "可愛溫暖的貓咪"),
                placeholder="例如：很貪吃但很黏人的虎斑貓，喜歡睡在書桌上",
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
        st.caption("💡 這些檔案直接放在 GitHub 的 `cat_photos/` 資料夾，永久保存不會掉。")

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

    st.divider()
    st.subheader("🎀 AI 鼓勵語預覽")
    if st.button("🎲 隨機產生一句鼓勵語"):
        with st.spinner(f"{cat_profile['cat_name']} 在想要說什麼..."):
            prompt = f"""請扮演一隻名叫「{cat_profile['cat_name']}」的貓咪，個性是「{cat_profile['cat_personality']}」。
請對主人 {NICKNAME} 說一句溫暖又可愛的鼓勵話，鼓勵她準備學測。
要求：用第一人稱「我」、20-40 字、有貓咪語氣（適度用「喵」）、不要太肉麻。"""
            msg = ask_ai(prompt, engine=engine)
            st.info(f"🐱 {cat_profile['cat_name']} 說：「{msg}」")


elif page == "💰 費用監控":
    st.header("💰 API 費用監控")

    usage = get_usage_stats()
    monthly_limit = float(st.secrets.get("MONTHLY_BUDGET_USD", "30"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日花費", f"${usage['today_usd']:.3f}", f"≈ NT${usage['today_usd']*32:.0f}")
    with col2:
        month_pct = min(usage["month_usd"] / monthly_limit * 100, 100)
        st.metric("本月花費", f"${usage['month_usd']:.2f}",
                  f"預算的 {month_pct:.0f}%")
    with col3:
        st.metric("今日呼叫次數", usage["today_calls"])

    st.markdown(f"""
    <div style="margin: 16px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span>本月預算 ${monthly_limit}</span>
            <span>{month_pct:.0f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width:{month_pct}%; background: {'#ef4444' if month_pct > 80 else '#f59e0b' if month_pct > 50 else '#10b981'};">
                ${usage['month_usd']:.2f}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if month_pct > 80:
        st.warning("⚠️ 本月預算即將用完")


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


# 頁尾
st.divider()
st.caption(
    f"💡 引擎：**{engine}** | 教材：{publisher}版 {grade}{subject} | "
    f"距學測 {phase_info['days_left']} 天 | v3.5"
)
