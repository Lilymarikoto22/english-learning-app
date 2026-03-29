import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def require_password() -> None:
    """パスワードが設定されている場合、未認証なら入力画面を表示して停止する。"""
    # Streamlit Cloud は st.secrets、ローカルは .env から取得
    try:
        correct = st.secrets["APP_PASSWORD"]
    except Exception:
        correct = os.getenv("APP_PASSWORD", "")
    if not correct:
        return  # パスワード未設定なら認証スキップ
    if st.session_state.get("authenticated"):
        return

    st.markdown("## 🔐 ログイン")
    pw = st.text_input("パスワードを入力", type="password")
    if st.button("ログイン"):
        if pw == correct:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    st.stop()
