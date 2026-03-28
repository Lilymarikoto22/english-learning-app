import random
import streamlit as st
from utils.vocab_store import get_all_words, add_word, update_review_count, delete_word
from utils.claude_client import get_example_sentence, get_recommended_words, get_api_key
from utils.streak_store import record_activity

st.set_page_config(page_title="Vocabulary", page_icon="📚", layout="centered")
record_activity()

col_t, col_i = st.columns([4, 1])
with col_t:
    st.title("📚 Vocabulary")
    st.markdown("新しい単語を保存して、フラッシュカードで復習しましょう。")
with col_i:
    st.image("assets/cat_study.png", width=120)
st.markdown("---")

# APIキーチェック
try:
    get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()

tab_save, tab_recommend, tab_review, tab_list = st.tabs(["➕ 単語を追加", "✨ おすすめ単語", "🃏 フラッシュカード", "📋 単語一覧"])


# ---- タブ1: 単語を追加 ----
with tab_save:
    st.subheader("新しい単語を追加")

    with st.form("add_word_form", clear_on_submit=True):
        new_word = st.text_input("単語", placeholder="例: persistent")
        new_definition = st.text_area(
            "意味・メモ",
            placeholder="例: しつこい、粘り強い / She is persistent in her efforts.",
            height=80,
        )
        submitted = st.form_submit_button("保存する", type="primary")

    if submitted:
        if new_word.strip() and new_definition.strip():
            add_word(new_word, new_definition)
            st.success(f"「{new_word}」を保存しました！")
        else:
            st.warning("単語と意味の両方を入力してください。")


# ---- タブ2: おすすめ単語 ----
with tab_recommend:
    st.subheader("レベル別おすすめ単語")
    st.markdown("レベルを選ぶと、Claude がおすすめの単語をリストアップします。")

    level = st.selectbox(
        "レベルを選ぶ",
        ["初級 (CEFR A1-A2)", "中級 (CEFR B1-B2)", "上級 (CEFR C1-C2)"],
    )

    if st.button("おすすめ単語を生成", type="primary"):
        with st.spinner("Claude が単語を考え中..."):
            try:
                recommended = get_recommended_words(level)
                st.session_state["recommended_words"] = recommended
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    if "recommended_words" in st.session_state and st.session_state["recommended_words"]:
        recommended = st.session_state["recommended_words"]
        st.markdown(f"**{level} の おすすめ単語：**")

        selected_words = []
        for i, w in enumerate(recommended):
            checked = st.checkbox(f"**{w['word']}** — {w['definition']}", key=f"rec_{i}", value=True)
            if checked:
                selected_words.append(w)

        if st.button("チェックした単語を単語帳に追加", use_container_width=True):
            for w in selected_words:
                add_word(w["word"], w["definition"])
            st.success(f"✅ {len(selected_words)} 語を単語帳に追加しました！")
            del st.session_state["recommended_words"]
            st.rerun()


# ---- タブ3: フラッシュカード ----
with tab_review:
    st.subheader("フラッシュカードで復習")

    words = get_all_words()

    if not words:
        st.info("まだ単語が保存されていません。「単語を追加」タブから追加してください。")
    else:
        # 優先度付き：review_count が少ない単語を優先（加重ランダム）
        weights = [max(1, 10 - w["review_count"]) for w in words]
        total = sum(weights)
        probabilities = [w / total for w in weights]

        if "card_index" not in st.session_state:
            st.session_state.card_index = random.choices(range(len(words)), weights=probabilities)[0]
            st.session_state.show_answer = False
            st.session_state.example_sentence = ""

        idx = st.session_state.card_index
        card = words[idx]

        # カード表示
        st.markdown(
            f"""
            <div style="
                background: #f0f4ff;
                border-radius: 12px;
                padding: 32px;
                text-align: center;
                margin: 16px 0;
            ">
                <h1 style="color: #1a1a2e; margin: 0;">{card['word']}</h1>
                <p style="color: #666; margin: 8px 0 0 0; font-size: 0.85em;">追加日: {card['added']} / 復習回数: {card['review_count']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 答えの表示
        if not st.session_state.show_answer:
            if st.button("定義を見る", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()
        else:
            st.markdown(
                f"""
                <div style="
                    background: #fff8e7;
                    border-radius: 8px;
                    padding: 16px;
                    margin: 8px 0;
                ">
                    <p style="margin: 0;">{card['definition']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 例文生成
            if st.button("Claude に例文を作ってもらう"):
                with st.spinner("例文を生成中..."):
                    st.session_state.example_sentence = get_example_sentence(
                        card["word"], card["definition"]
                    )

            if st.session_state.example_sentence:
                st.markdown("**例文:**")
                st.markdown(st.session_state.example_sentence)

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ 覚えた", use_container_width=True, type="primary"):
                    update_review_count(idx, 1)
                    st.session_state.card_index = random.choices(
                        range(len(words)), weights=probabilities
                    )[0]
                    st.session_state.show_answer = False
                    st.session_state.example_sentence = ""
                    st.rerun()

            with col2:
                if st.button("❌ まだ", use_container_width=True):
                    update_review_count(idx, -1)
                    st.session_state.card_index = random.choices(
                        range(len(words)), weights=probabilities
                    )[0]
                    st.session_state.show_answer = False
                    st.session_state.example_sentence = ""
                    st.rerun()

        st.caption(f"保存済み単語: {len(words)} 語")


# ---- タブ3: 単語一覧 ----
with tab_list:
    st.subheader("保存した単語一覧")

    words = get_all_words()

    if not words:
        st.info("まだ単語が保存されていません。")
    else:
        for i, w in enumerate(words):
            with st.expander(f"{w['word']}  —  {w['definition'][:40]}..."):
                st.markdown(f"**単語:** {w['word']}")
                st.markdown(f"**意味:** {w['definition']}")
                st.markdown(f"**追加日:** {w['added']}  /  **復習回数:** {w['review_count']}")
                if st.button("削除", key=f"del_{i}"):
                    delete_word(i)
                    st.rerun()
