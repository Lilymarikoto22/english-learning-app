import os
import random
import streamlit as st
from utils.vocab_store import get_all_words, get_words_by_level, add_word, update_review_count, delete_word
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

try:
    get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()

LEVELS = ["", "初級", "中級", "上級"]
LEVEL_LABELS = {"": "なし", "初級": "初級", "中級": "中級", "上級": "上級"}

tab_save, tab_recommend, tab_review, tab_list, tab_battle = st.tabs([
    "➕ 単語を追加", "✨ おすすめ単語・熟語", "🃏 フラッシュカード", "📋 単語一覧", "⚔️ バトルクイズ"
])


# ---- タブ1: 単語を追加 ----
with tab_save:
    st.subheader("新しい単語を追加")

    with st.form("add_word_form", clear_on_submit=True):
        new_word = st.text_input("単語・熟語", placeholder="例: persistent / give up")
        new_definition = st.text_area(
            "意味・メモ",
            placeholder="例: しつこい、粘り強い",
            height=80,
        )
        new_pronunciation = st.text_input("発音記号 (IPA)", placeholder="例: /pərˈsɪstənt/")
        col_pos, col_vt = st.columns(2)
        with col_pos:
            new_pos = st.selectbox("品詞", ["", "名詞", "動詞", "形容詞", "副詞", "熟語", "その他"])
        with col_vt:
            new_verb_type = st.selectbox("動詞の種類", ["", "他動詞", "自動詞", "両方"])
        new_level = st.selectbox("難易度レベル", ["なし", "初級", "中級", "上級"])
        submitted = st.form_submit_button("保存する", type="primary")

    if submitted:
        if new_word.strip() and new_definition.strip():
            level_val = "" if new_level == "なし" else new_level
            add_word(new_word, new_definition, level=level_val,
                     pos=new_pos, verb_type=new_verb_type, pronunciation=new_pronunciation)
            st.success(f"「{new_word}」を保存しました！")
        else:
            st.warning("単語と意味の両方を入力してください。")


# ---- タブ2: おすすめ単語・熟語 ----
with tab_recommend:
    st.subheader("レベル別おすすめ単語・熟語")
    st.markdown("レベルを選ぶと、Claude がおすすめの単語と熟語をリストアップします。")

    CEFR_LEVELS = ["初級 (CEFR A1-A2)", "中級 (CEFR B1-B2)", "上級 (CEFR C1-C2)"]
    CEFR_TO_LEVEL = {
        "初級 (CEFR A1-A2)": "初級",
        "中級 (CEFR B1-B2)": "中級",
        "上級 (CEFR C1-C2)": "上級",
    }
    cefr_label = st.selectbox("レベルを選ぶ", CEFR_LEVELS)

    if st.button("おすすめ単語を生成", type="primary"):
        with st.spinner("Claude が単語を考え中..."):
            try:
                recommended = get_recommended_words(cefr_label)
                st.session_state["recommended_words"] = recommended
                st.session_state["recommended_level"] = CEFR_TO_LEVEL[cefr_label]
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    if "recommended_words" in st.session_state and st.session_state["recommended_words"]:
        recommended = st.session_state["recommended_words"]
        rec_level = st.session_state.get("recommended_level", "")
        st.markdown(f"**{cefr_label} のおすすめ単語：**")

        selected_words = []
        for i, w in enumerate(recommended):
            checked = st.checkbox(f"**{w['word']}** — {w['definition']}", key=f"rec_{i}", value=True)
            if checked:
                selected_words.append(w)

        if st.button("チェックした単語を単語帳に追加", use_container_width=True):
            for w in selected_words:
                add_word(w["word"], w["definition"], level=rec_level,
                         pos=w.get("pos", ""), verb_type=w.get("verb_type", ""),
                         pronunciation=w.get("pronunciation", ""))
            st.success(f"✅ {len(selected_words)} 語を単語帳に追加しました！（レベル: {rec_level}）")
            del st.session_state["recommended_words"]
            st.rerun()


# ---- タブ3: フラッシュカード ----
with tab_review:
    st.subheader("フラッシュカードで復習")
    words = get_all_words()

    if not words:
        st.info("まだ単語が保存されていません。「単語を追加」タブから追加してください。")
    else:
        weights = [max(1, 10 - w.get("review_count", 0)) for w in words]
        total = sum(weights)
        probabilities = [w / total for w in weights]

        if "card_index" not in st.session_state:
            st.session_state.card_index = random.choices(range(len(words)), weights=probabilities)[0]
            st.session_state.show_answer = False
            st.session_state.example_sentence = ""

        idx = st.session_state.card_index
        card = words[idx]
        level_badge = f" `{card.get('level', '')}`" if card.get("level") else ""

        pos_label = card.get("pos", "")
        vt_label = card.get("verb_type", "")
        pron_label = card.get("pronunciation", "")
        level_label = card.get("level", "")

        badges = " &nbsp;".join(f'<span style="background:#dbeafe;color:#1e3a8a;border-radius:4px;padding:2px 7px;font-size:0.8em;">{b}</span>'
                                for b in [pos_label, vt_label, level_label] if b)
        pron_html = f'<p style="color:#6366f1;margin:4px 0;font-size:1em;">{pron_label}</p>' if pron_label else ""

        st.markdown(
            f"""
            <div style="
                background: #f0f4ff; border-radius: 12px;
                padding: 32px; text-align: center; margin: 16px 0;
            ">
                <h1 style="color: #1a1a2e; margin: 0;">{card['word']}</h1>
                {pron_html}
                <div style="margin:8px 0;">{badges}</div>
                <p style="color: #666; margin: 4px 0 0 0; font-size: 0.8em;">復習回数: {card.get('review_count', 0)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.show_answer:
            if st.button("定義を見る", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()
        else:
            st.markdown(
                f"""
                <div style="background:#fff8e7; border-radius:8px; padding:16px; margin:8px 0;">
                    <p style="margin:0;">{card['definition']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Claude に例文を作ってもらう"):
                with st.spinner("例文を生成中..."):
                    st.session_state.example_sentence = get_example_sentence(card["word"], card["definition"])

            if st.session_state.example_sentence:
                st.markdown("**例文:**")
                st.markdown(st.session_state.example_sentence)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 覚えた", use_container_width=True, type="primary"):
                    update_review_count(idx, 1)
                    st.session_state.card_index = random.choices(range(len(words)), weights=probabilities)[0]
                    st.session_state.show_answer = False
                    st.session_state.example_sentence = ""
                    st.rerun()
            with col2:
                if st.button("❌ まだ", use_container_width=True):
                    update_review_count(idx, -1)
                    st.session_state.card_index = random.choices(range(len(words)), weights=probabilities)[0]
                    st.session_state.show_answer = False
                    st.session_state.example_sentence = ""
                    st.rerun()

        st.caption(f"保存済み単語: {len(words)} 語")


# ---- タブ4: 単語一覧 ----
with tab_list:
    st.subheader("保存した単語一覧")
    words = get_all_words()

    if not words:
        st.info("まだ単語が保存されていません。")
    else:
        for i, w in enumerate(words):
            level_tag = f"[{w['level']}] " if w.get("level") else ""
            with st.expander(f"{level_tag}{w['word']}  —  {w['definition'][:40]}"):
                st.markdown(f"**単語:** {w['word']}")
                if w.get("pronunciation"):
                    st.markdown(f"**発音:** {w['pronunciation']}")
                info_parts = [p for p in [w.get("pos", ""), w.get("verb_type", "")] if p]
                if info_parts:
                    st.markdown(f"**品詞:** {'　'.join(info_parts)}")
                st.markdown(f"**意味:** {w['definition']}")
                if w.get("level"):
                    st.markdown(f"**レベル:** {w['level']}")
                st.markdown(f"**復習回数:** {w.get('review_count', 0)}")
                if st.button("削除", key=f"del_{i}"):
                    delete_word(i)
                    st.rerun()


# ---- タブ5: バトルクイズ ----
with tab_battle:

    COURSE_OPTIONS = ["初級", "中級", "上級"]
    MONSTER_IMAGES = {
        "初級": "assets/fantasy_game_character_slime.png",
        "中級": "assets/fantasy_goblin.png",
        "上級": "assets/dragon_fire4_yellow.png",
    }
    HERO_IMAGE = "assets/yuusya_game.png"

    def _short_def(definition: str) -> str:
        """'日本語の意味 / example sentence' から日本語部分だけ返す。"""
        return definition.split("/")[0].strip()

    def build_questions(words: list[dict]) -> list[dict]:
        pool = [w for w in words if w.get("word") and w.get("definition")]
        if len(pool) < 3:
            return []
        selected = random.sample(pool, min(10, len(pool)))
        questions = []
        for i, w in enumerate(selected):
            q_type = "word2def" if i % 2 == 0 else "def2word"
            wrong_pool = [x for x in pool if x["id"] != w["id"]]
            wrongs = random.sample(wrong_pool, min(2, len(wrong_pool)))
            if len(wrongs) < 2:
                continue
            if q_type == "word2def":
                choices = [_short_def(w["definition"])] + [_short_def(x["definition"]) for x in wrongs]
            else:
                choices = [w["word"]] + [x["word"] for x in wrongs]
            random.shuffle(choices)
            correct = _short_def(w["definition"]) if q_type == "word2def" else w["word"]
            answer_idx = choices.index(correct)
            questions.append({
                "word": w["word"],
                "definition": _short_def(w["definition"]),
                "q_type": q_type,
                "choices": choices,
                "answer_idx": answer_idx,
            })
        return questions[:10]

    def reset_battle():
        for k in ["bq_questions", "bq_current", "bq_score", "bq_hp",
                  "bq_wrong", "bq_phase", "bq_last_correct", "bq_feedback"]:
            st.session_state.pop(k, None)

    # ── フェーズ: コース選択 ──
    if st.session_state.get("bq_phase") not in ("playing", "result"):
        st.subheader("⚔️ バトルクイズ")
        st.markdown("単語の力で敵モンスターを倒せ！**7問正解**でコースクリア。")

        course = st.selectbox("コースを選ぶ", COURSE_OPTIONS, key="bq_course_select")
        course_words = get_words_by_level(course)

        st.markdown(f"**{course}コース**の単語: {len(course_words)} 語")
        if len(course_words) < 3:
            st.warning(f"⚠️ {course}コースの単語が少なすぎます（最低3語必要）。単語を追加してからチャレンジしてください！")
        else:
            if st.button("🗡️ バトル開始！", type="primary", use_container_width=True):
                questions = build_questions(course_words)
                if not questions:
                    st.error("問題を生成できませんでした。")
                else:
                    st.session_state["bq_questions"] = questions
                    st.session_state["bq_current"] = 0
                    st.session_state["bq_score"] = 0
                    st.session_state["bq_hp"] = 3
                    st.session_state["bq_wrong"] = []
                    st.session_state["bq_phase"] = "playing"
                    st.session_state["bq_last_correct"] = None
                    st.session_state["bq_feedback"] = ""
                    st.session_state["bq_selected_course"] = course
                    st.rerun()

    # ── フェーズ: プレイ中 ──
    elif st.session_state.get("bq_phase") == "playing":
        questions = st.session_state["bq_questions"]
        current = st.session_state["bq_current"]
        score = st.session_state["bq_score"]
        hp = st.session_state["bq_hp"]
        course = st.session_state.get("bq_selected_course", "初級")

        # HP と進捗
        hearts = "❤️" * hp + "🖤" * (3 - hp)
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center;
                        background:#fff; border:1px solid #bfdbfe; border-radius:10px;
                        padding:10px 16px; margin-bottom:12px;">
                <div style="font-size:1.4em;">{hearts}</div>
                <div style="color:#64748b; font-size:0.9em;">問題 {current + 1} / {len(questions)}</div>
                <div style="color:#16a34a; font-weight:bold;">✅ {score}問正解</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # バトル画面
        monster_img = MONSTER_IMAGES.get(course, "assets/monster_easy.png")
        col_hero, col_vs, col_mon = st.columns([2, 1, 2])
        with col_hero:
            if os.path.exists(HERO_IMAGE):
                st.image(HERO_IMAGE, width=120)
            else:
                st.markdown("<div style='font-size:4em; text-align:center;'>🧒</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-size:0.8em; color:#64748b;'>プレイヤー</div>", unsafe_allow_html=True)

        with col_vs:
            # 直前の結果フィードバック
            feedback = st.session_state.get("bq_feedback", "")
            if feedback:
                st.markdown(f"<div style='text-align:center; font-size:1.4em; margin-top:30px;'>{feedback}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center; font-size:1.8em; margin-top:30px;'>⚔️</div>", unsafe_allow_html=True)

        with col_mon:
            if os.path.exists(monster_img):
                st.image(monster_img, width=120)
            else:
                st.markdown("<div style='font-size:4em; text-align:center;'>👾</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-size:0.8em; color:#64748b;'>モンスター</div>", unsafe_allow_html=True)

        st.markdown("---")

        # 問題
        q = questions[current]
        if q["q_type"] == "word2def":
            st.markdown(f"### この単語の意味は？")
            st.markdown(
                f"""<div style="background:#dbeafe; border-radius:10px; padding:16px 24px;
                              text-align:center; font-size:1.6em; font-weight:bold;
                              color:#1e3a8a; margin:12px 0;">
                    {q['word']}
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"### この意味の英単語は？")
            st.markdown(
                f"""<div style="background:#dcfce7; border-radius:10px; padding:16px 24px;
                              text-align:center; font-size:1.1em;
                              color:#14532d; margin:12px 0;">
                    {q['definition']}
                </div>""",
                unsafe_allow_html=True,
            )

        # 選択肢ボタン
        for ci, choice in enumerate(q["choices"]):
            if st.button(f"{'①②③'[ci]}  {choice}", key=f"choice_{current}_{ci}", use_container_width=True):
                correct = (ci == q["answer_idx"])
                if correct:
                    st.session_state["bq_score"] += 1
                    st.session_state["bq_feedback"] = "🗡️ ヒット！"
                else:
                    st.session_state["bq_hp"] -= 1
                    st.session_state["bq_wrong"].append(q)
                    st.session_state["bq_feedback"] = "💥 ダメージ！"

                next_q = current + 1
                # ゲームオーバー判定
                if st.session_state["bq_hp"] <= 0:
                    st.session_state["bq_phase"] = "result"
                    st.session_state["bq_feedback"] = ""
                elif next_q >= len(questions):
                    st.session_state["bq_phase"] = "result"
                    st.session_state["bq_feedback"] = ""
                else:
                    st.session_state["bq_current"] = next_q
                st.rerun()

    # ── フェーズ: 結果 ──
    elif st.session_state.get("bq_phase") == "result":
        score = st.session_state["bq_score"]
        hp = st.session_state["bq_hp"]
        wrong = st.session_state["bq_wrong"]
        total = len(st.session_state["bq_questions"])
        cleared = score >= 7 and hp > 0

        if cleared:
            st.markdown(
                f"""
                <div style="background:linear-gradient(135deg,#dcfce7,#bbf7d0);
                            border:2px solid #22c55e; border-radius:16px;
                            padding:28px; text-align:center; margin:12px 0;">
                    <div style="font-size:3em;">🏆</div>
                    <div style="font-size:1.8em; font-weight:bold; color:#15803d; margin:8px 0;">コースクリア！</div>
                    <div style="font-size:1.1em; color:#166534;">{total}問中 {score}問正解！</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.balloons()
        else:
            reason = "HPがなくなりました…" if hp <= 0 else "あと少し！"
            st.markdown(
                f"""
                <div style="background:linear-gradient(135deg,#fee2e2,#fecaca);
                            border:2px solid #ef4444; border-radius:16px;
                            padding:28px; text-align:center; margin:12px 0;">
                    <div style="font-size:3em;">💀</div>
                    <div style="font-size:1.8em; font-weight:bold; color:#b91c1c; margin:8px 0;">ゲームオーバー</div>
                    <div style="font-size:1.1em; color:#991b1b;">{reason}　{total}問中 {score}問正解</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 間違えた単語の復習
        if wrong:
            st.markdown("---")
            st.subheader(f"📝 間違えた単語（{len(wrong)}語）")
            for w in wrong:
                st.markdown(
                    f"""
                    <div style="background:#fff; border:1px solid #fca5a5; border-radius:8px;
                                padding:12px 16px; margin:6px 0;">
                        <b style="color:#1e3a8a; font-size:1.1em;">{w['word']}</b>
                        <span style="color:#64748b; margin-left:12px;">{w['definition']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("全問正解！間違いなし！🎉")

        st.markdown("---")
        if st.button("🔄 もう一度チャレンジ", type="primary", use_container_width=True):
            reset_battle()
            st.rerun()
