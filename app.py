import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="英語学習アプリ",
    page_icon="🎧",
    layout="centered",
)

# ── グローバル CSS ──────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebarNav"] { padding-top: 1rem; }

  .stButton > button {
    border-radius: 10px;
    font-weight: 600;
  }

  /* カード */
  .card {
    background: #ffffff;
    border: 1px solid #bfdbfe;
    border-radius: 14px;
    padding: 20px 24px;
    margin: 10px 0;
    box-shadow: 0 2px 10px rgba(37,99,235,0.08);
  }

  /* ストリークバッジ */
  .streak-badge {
    display: inline-block;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #fff;
    font-size: 2.4em;
    font-weight: 900;
    border-radius: 16px;
    padding: 12px 28px;
    letter-spacing: 1px;
    box-shadow: 0 4px 18px rgba(34,197,94,0.3);
  }

  .streak-label {
    font-size: 0.85em;
    color: #64748b;
    margin-top: 6px;
  }

  /* マイルストーン */
  .milestone-box {
    background: linear-gradient(135deg, #eff6ff, #dbeafe);
    border: 2px solid #2563eb;
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    margin: 12px 0;
  }
</style>
""", unsafe_allow_html=True)

# ── streak ────────────────────────────────────────────────
from utils.streak_store import (
    get_streak, studied_today, get_total_days,
    render_calendar_html, pop_new_milestone,
)

streak = get_streak()
done_today = studied_today()
total_days = get_total_days()

# マイルストーン確認
milestone_n, milestone_msg = pop_new_milestone()
if milestone_n:
    st.balloons()
    icon, title, body = milestone_msg
    if milestone_n >= 30:
        m_img = "assets/yuuenchi_parade_float1_cake.png"
    elif milestone_n >= 10:
        m_img = "assets/trophy_businesswoman.png"
    else:
        m_img = "assets/seikou_banzai_woman.png"

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.markdown(f"""
        <div class="milestone-box">
          <div style="font-size:3em;">{icon}</div>
          <div style="font-size:1.6em; font-weight:bold; color:#2563eb; margin:8px 0;">{title}</div>
          <div style="color:#1e293b; font-size:1em;">{body}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.image(m_img, width=130)

# ── ヘッダー ──────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("## 🎧 英語学習アプリ")
    st.markdown("毎日続けて英語力アップ！")
with col_h2:
    st.image("assets/english_book_girl.png", width=110)
st.markdown("---")

# ── ストリーク表示 ────────────────────────────────────────
col_s, col_t, col_img = st.columns([5, 5, 2])

with col_s:
    fire = "🔥" if streak >= 3 else "📅"
    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <div style="font-size:0.8em; color:#64748b; letter-spacing:1px; margin-bottom:8px;">CURRENT STREAK</div>
      <div class="streak-badge">{fire} {streak}日</div>
      <div class="streak-label">{'✅ 今日学習済み！' if done_today else '⏳ 今日はまだ学習していません'}</div>
    </div>
    """, unsafe_allow_html=True)

with col_t:
    st.markdown(f"""
    <div class="card" style="text-align:center;">
      <div style="font-size:0.8em; color:#64748b; letter-spacing:1px; margin-bottom:8px;">TOTAL DAYS</div>
      <div class="streak-badge" style="background:linear-gradient(135deg,#3b82f6,#1d4ed8); box-shadow:0 4px 18px rgba(59,130,246,0.3);">
        📚 {total_days}日
      </div>
      <div class="streak-label">累計学習日数</div>
    </div>
    """, unsafe_allow_html=True)

with col_img:
    st.image("assets/line_ashiato03_cat.png", width=80)

# ── 次のマイルストーン ─────────────────────────────────────
MILESTONES = [3, 7, 10, 14, 20, 30, 50, 100]
next_m = next((m for m in MILESTONES if m > streak), None)
if next_m:
    remaining = next_m - streak
    progress = streak / next_m
    st.markdown(f"""
    <div class="card">
      <div style="font-size:0.85em; color:#475569; margin-bottom:8px;">
        🎯 次のマイルストーン：<b style="color:#d97706;">{next_m}日連続</b>
        　あと <b style="color:#16a34a;">{remaining}日</b>
      </div>
      <div style="background:#e2e8f0; border-radius:8px; height:10px; overflow:hidden;">
        <div style="width:{int(progress*100)}%; background:linear-gradient(90deg,#22c55e,#4ade80);
                    height:100%; border-radius:8px;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── カレンダー ────────────────────────────────────────────
col_cal_title, col_cal_img = st.columns([5, 1])
with col_cal_title:
    st.markdown("### 📅 学習カレンダー")
with col_cal_img:
    st.image("assets/calender_woman.png", width=70)
st.markdown("""
<div style="font-size:0.8em; color:#64748b; margin-bottom:8px;">
  🟢 学習済み　🟡 今日（未学習）　○ 学習なし
</div>
""", unsafe_allow_html=True)
st.markdown(render_calendar_html(num_months=3), unsafe_allow_html=True)

# ── ナビゲーション ────────────────────────────────────────
st.markdown("---")
st.markdown("### 学習メニュー")

cols = st.columns(3)
menus = [
    ("💬", "Conversation", "AIと英会話練習"),
    ("📚", "Vocabulary", "単語帳・フラッシュカード"),
    ("🗞️", "Shadowing", "ニュース記事でシャドウイング"),
    ("🎭", "Dialogue", "British Englishフレーズ学習"),
]

for i, (icon, name, desc) in enumerate(menus):
    with cols[i % 3]:
        st.markdown(f"""
        <div class="card" style="text-align:center; min-height:90px;">
          <div style="font-size:1.8em;">{icon}</div>
          <div style="font-weight:bold; color:#1e293b;">{name}</div>
          <div style="font-size:0.75em; color:#64748b; margin-top:4px;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

if not os.getenv("ANTHROPIC_API_KEY"):
    st.warning("⚠️ ANTHROPIC_API_KEY が設定されていません。`.env` ファイルを確認してください。")
