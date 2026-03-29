import os
import random
import streamlit as st
from utils.vocab_store import get_all_words, get_words_by_level, add_word, update_review_count, delete_word
from utils.claude_client import get_example_sentence, get_recommended_words, get_api_key
from utils.streak_store import record_activity
from utils.pet_store import grant_exp, show_pet_notifications

st.set_page_config(page_title="Vocabulary", page_icon="📚", layout="centered")
record_activity()
show_pet_notifications()

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


@st.cache_data(ttl=300, show_spinner=False)
def _cached_all_words():
    return get_all_words()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_words_by_level(level: str):
    return get_words_by_level(level)

tab_save, tab_recommend, tab_review, tab_list, tab_battle = st.tabs([
    "➕ 単語を追加", "✨ おすすめ単語・熟語", "🃏 フラッシュカード", "📋 単語一覧", "⚔️ バトルクイズ"
])

# 全単語を1回だけ取得してタブ間で共有
all_words = _cached_all_words()


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
        col_lv, col_toeic = st.columns(2)
        with col_lv:
            new_level = st.selectbox("難易度レベル", ["なし", "初級", "中級", "上級"])
        with col_toeic:
            new_toeic = st.selectbox("TOEIC目標スコア", ["なし", "600", "800", "990"])
        submitted = st.form_submit_button("保存する", type="primary")

    if submitted:
        if new_word.strip() and new_definition.strip():
            level_val = "" if new_level == "なし" else new_level
            toeic_val = "" if new_toeic == "なし" else new_toeic
            add_word(new_word, new_definition, level=level_val,
                     pos=new_pos, verb_type=new_verb_type, pronunciation=new_pronunciation,
                     toeic_target=toeic_val)
            _cached_all_words.clear()
            _cached_words_by_level.clear()
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
                         pronunciation=w.get("pronunciation", ""),
                         toeic_target=w.get("toeic_target", ""))
            _cached_all_words.clear()
            _cached_words_by_level.clear()
            st.success(f"✅ {len(selected_words)} 語を単語帳に追加しました！（レベル: {rec_level}）")
            del st.session_state["recommended_words"]
            st.rerun()


# ---- タブ3: フラッシュカード ----
with tab_review:
    st.subheader("フラッシュカードで復習")
    words = all_words

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
                    grant_exp(10)
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
    words = all_words

    if not words:
        st.info("まだ単語が保存されていません。")
    else:
        LEVEL_ORDER = {"初級": 0, "中級": 1, "上級": 2, "": 3}
        TOEIC_ORDER = {"600": 0, "800": 1, "990": 2, "": 3}
        TOEIC_COLOR = {"600": "#dcfce7", "800": "#dbeafe", "990": "#fef9c3"}

        col_f1, col_f2, col_s = st.columns(3)
        with col_f1:
            filter_level = st.selectbox("レベルで絞り込み", ["全て", "初級", "中級", "上級", "なし"], key="list_filter")
        with col_f2:
            filter_toeic = st.selectbox("TOEICで絞り込み", ["全て", "600", "800", "990"], key="list_toeic_filter")
        with col_s:
            sort_by = st.selectbox("並び順", [
                "登録順", "レベル順（初級→上級）", "レベル順（上級→初級）",
                "TOEIC優先（600→990）", "復習回数が少ない順"
            ], key="list_sort")

        display_words = list(words)

        # 絞り込み
        if filter_level == "なし":
            display_words = [w for w in display_words if not w.get("level")]
        elif filter_level != "全て":
            display_words = [w for w in display_words if w.get("level") == filter_level]

        if filter_toeic != "全て":
            display_words = [w for w in display_words if w.get("toeic_target") == filter_toeic]

        # 並び替え
        if sort_by == "レベル順（初級→上級）":
            display_words.sort(key=lambda w: LEVEL_ORDER.get(w.get("level", ""), 3))
        elif sort_by == "レベル順（上級→初級）":
            display_words.sort(key=lambda w: -LEVEL_ORDER.get(w.get("level", ""), 3))
        elif sort_by == "TOEIC優先（600→990）":
            display_words.sort(key=lambda w: TOEIC_ORDER.get(w.get("toeic_target", ""), 3))
        elif sort_by == "復習回数が少ない順":
            display_words.sort(key=lambda w: w.get("review_count", 0))

        st.caption(f"{len(display_words)} 語表示中（全 {len(words)} 語）")

        for i, w in enumerate(display_words):
            # 意味と例文を分離
            def_parts = w["definition"].split("/", 1)
            meaning = def_parts[0].strip()
            example = def_parts[1].strip() if len(def_parts) > 1 else ""

            level_tag = f"[{w['level']}] " if w.get("level") else ""
            toeic_tag = f"[TOEIC{w['toeic_target']}] " if w.get("toeic_target") else ""
            with st.expander(f"{toeic_tag}{level_tag}{w['word']}  —  {meaning[:40]}"):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**単語・熟語:** {w['word']}")
                    if w.get("pronunciation"):
                        st.markdown(f"**発音:** `{w['pronunciation']}`")
                    info_parts = [p for p in [w.get("pos", ""), w.get("verb_type", "")] if p]
                    if info_parts:
                        st.markdown(f"**品詞:** {'　'.join(info_parts)}")
                    st.markdown(f"**意味:** {meaning}")
                    if example:
                        st.markdown(f"**例文:** *{example}*")
                    tags = []
                    if w.get("level"):
                        tags.append(f"レベル: {w['level']}")
                    if w.get("toeic_target"):
                        tags.append(f"TOEIC: {w['toeic_target']}点")
                    if tags:
                        st.markdown(f"**{' ／ '.join(tags)}**")
                    st.markdown(f"**復習回数:** {w.get('review_count', 0)}")
                with col_b:
                    orig_idx = words.index(w)
                    if st.button("削除", key=f"del_{i}"):
                        delete_word(orig_idx)
                        _cached_all_words.clear()
                        _cached_words_by_level.clear()
                        st.rerun()


# ---- タブ5: バトルクイズ ----
_BQ_COURSE_OPTIONS = ["初級", "中級", "上級"]
_BQ_HERO_IMAGE = "assets/yuusya_game.png"
_BQ_MONSTERS = [
    {"name": "スライム", "img": "assets/fantasy_game_character_slime.png", "emoji": "🟢"},
    {"name": "ゴブリン", "img": "assets/fantasy_goblin.png",               "emoji": "👺"},
    {"name": "オーク",   "img": "assets/fantasy_orc.png",                  "emoji": "💚"},
    {"name": "ドラゴン", "img": "assets/dragon_fire4_yellow.png",          "emoji": "🐉"},
]
_BQ_TOTAL_Q = 20
_BQ_Q_PER_MONSTER = 5
_BQ_PLAYER_HP = 5


def _short_def(definition: str) -> str:
    return definition.split("/")[0].strip()


def _build_questions(words: list[dict]) -> list[dict]:
    pool = [w for w in words if w.get("word") and w.get("definition")]
    if len(pool) < 3:
        return []
    idioms     = [w for w in pool if w.get("pos") == "熟語"]
    non_idioms = [w for w in pool if w.get("pos") != "熟語"]
    n_idiom = min(8, len(idioms))
    n_word  = min(_BQ_TOTAL_Q - n_idiom, len(non_idioms))
    selected = (random.sample(non_idioms, n_word) +
                (random.sample(idioms, n_idiom) if n_idiom else []))
    random.shuffle(selected)
    selected = selected[:_BQ_TOTAL_Q]
    questions = []
    for i, w in enumerate(selected):
        q_type = "word2def" if i % 2 == 0 else "def2word"
        wrong_pool = [x for x in pool if x["id"] != w["id"]]
        if len(wrong_pool) < 2:
            continue
        wrongs = random.sample(wrong_pool, 2)
        if q_type == "word2def":
            choices = [_short_def(w["definition"])] + [_short_def(x["definition"]) for x in wrongs]
        else:
            choices = [w["word"]] + [x["word"] for x in wrongs]
        random.shuffle(choices)
        correct = _short_def(w["definition"]) if q_type == "word2def" else w["word"]
        questions.append({
            "word": w["word"],
            "definition": _short_def(w["definition"]),
            "q_type": q_type,
            "choices": choices,
            "answer_idx": choices.index(correct),
        })
    return questions[:_BQ_TOTAL_Q]


def _reset_battle():
    for k in ["bq_questions", "bq_current", "bq_score", "bq_hp",
              "bq_wrong", "bq_phase", "bq_feedback", "bq_exp_granted", "bq_monster_idx"]:
        st.session_state.pop(k, None)


@st.fragment
def _battle_quiz_ui():
    phase = st.session_state.get("bq_phase", "select")

    # ── フェーズ: コース選択 ──────────────────────────────────
    if phase == "select":
        st.subheader("⚔️ バトルクイズ")
        st.markdown("4体のモンスターを倒せ！合計20問。HPを守り切ってクリアしよう。")

        course = st.selectbox("コースを選ぶ", _BQ_COURSE_OPTIONS, key="bq_course_select")

        if st.button("🗡️ バトル開始！", type="primary", use_container_width=True):
            with st.spinner("単語を読み込み中..."):
                course_words = _cached_words_by_level(course)
            if len(course_words) < 10:
                st.warning("単語が少なすぎます（最低10語必要）。")
            else:
                questions = _build_questions(course_words)
                if not questions:
                    st.error("問題を生成できませんでした。")
                else:
                    st.session_state.update({
                        "bq_questions": questions,
                        "bq_current": 0,
                        "bq_score": 0,
                        "bq_hp": _BQ_PLAYER_HP,
                        "bq_wrong": [],
                        "bq_phase": "playing",
                        "bq_feedback": "",
                        "bq_monster_idx": 0,
                        "bq_selected_course": course,
                    })
                    st.rerun()

    # ── フェーズ: モンスター撃破トランジション ────────────────
    elif phase == "monster_clear":
        defeated = _BQ_MONSTERS[st.session_state.get("bq_monster_idx", 0) - 1]
        next_mon = _BQ_MONSTERS[st.session_state.get("bq_monster_idx", 0)]
        st.markdown(
            f"""<div style="background:linear-gradient(135deg,#dcfce7,#bbf7d0);
                            border:2px solid #22c55e; border-radius:16px;
                            padding:24px; text-align:center; margin:12px 0;">
                <div style="font-size:2.5em;">⚔️✨</div>
                <div style="font-size:1.5em; font-weight:bold; color:#15803d; margin:8px 0;">
                    {defeated['name']}を倒した！
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        hearts = "❤️" * st.session_state["bq_hp"] + "🖤" * (_BQ_PLAYER_HP - st.session_state["bq_hp"])
        st.markdown(f"現在のHP: {hearts}")
        st.markdown(f"### 次の敵: {next_mon['emoji']} **{next_mon['name']}**")
        if os.path.exists(next_mon["img"]):
            st.image(next_mon["img"], width=120)
        if st.button(f"🗡️ {next_mon['name']}と戦う！", type="primary", use_container_width=True):
            st.session_state["bq_phase"] = "playing"
            st.session_state["bq_feedback"] = ""
            st.rerun()

    # ── フェーズ: プレイ中 ───────────────────────────────────
    elif phase == "playing":
        questions    = st.session_state["bq_questions"]
        current      = st.session_state["bq_current"]
        score        = st.session_state["bq_score"]
        hp           = st.session_state["bq_hp"]
        monster_idx  = st.session_state.get("bq_monster_idx", 0)
        monster      = _BQ_MONSTERS[monster_idx]
        q_in_monster = current % _BQ_Q_PER_MONSTER

        hearts = "❤️" * hp + "🖤" * (_BQ_PLAYER_HP - hp)
        st.markdown(
            f"""<div style="display:flex; justify-content:space-between; align-items:center;
                            background:#fff; border:1px solid #bfdbfe; border-radius:10px;
                            padding:10px 16px; margin-bottom:8px;">
                <div style="font-size:1.2em;">{hearts}</div>
                <div style="color:#64748b; font-size:0.85em;">
                    {monster['emoji']} {monster['name']}（{monster_idx+1}/4体目）
                    問題 {q_in_monster+1}/{_BQ_Q_PER_MONSTER}
                </div>
                <div style="color:#16a34a; font-weight:bold;">✅ {score}問</div>
            </div>""",
            unsafe_allow_html=True,
        )

        col_hero, col_vs, col_mon = st.columns([2, 1, 2])
        with col_hero:
            if os.path.exists(_BQ_HERO_IMAGE):
                st.image(_BQ_HERO_IMAGE, width=110)
            else:
                st.markdown("<div style='font-size:4em;text-align:center;'>🧒</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;font-size:0.8em;color:#64748b;'>プレイヤー</div>", unsafe_allow_html=True)

        with col_vs:
            fb = st.session_state.get("bq_feedback", "")
            st.markdown(f"<div style='text-align:center;font-size:1.6em;margin-top:28px;'>{fb or '⚔️'}</div>", unsafe_allow_html=True)

        with col_mon:
            if os.path.exists(monster["img"]):
                st.image(monster["img"], width=110)
            else:
                st.markdown(f"<div style='font-size:4em;text-align:center;'>{monster['emoji']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center;font-size:0.8em;color:#64748b;'>{monster['name']}</div>", unsafe_allow_html=True)

        st.markdown("---")

        q = questions[current]
        if q["q_type"] == "word2def":
            st.markdown("### この単語の意味は？")
            st.markdown(
                f"""<div style="background:#dbeafe;border-radius:10px;padding:16px 24px;
                              text-align:center;font-size:1.6em;font-weight:bold;
                              color:#1e3a8a;margin:12px 0;">{q['word']}</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("### この意味の英単語・熟語は？")
            st.markdown(
                f"""<div style="background:#dcfce7;border-radius:10px;padding:16px 24px;
                              text-align:center;font-size:1.1em;
                              color:#14532d;margin:12px 0;">{q['definition']}</div>""",
                unsafe_allow_html=True,
            )

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
                if st.session_state["bq_hp"] <= 0:
                    st.session_state["bq_phase"] = "result"
                    st.session_state["bq_feedback"] = ""
                elif next_q >= len(questions):
                    st.session_state["bq_phase"] = "result"
                    st.session_state["bq_feedback"] = ""
                elif next_q % _BQ_Q_PER_MONSTER == 0:
                    st.session_state["bq_monster_idx"] = monster_idx + 1
                    st.session_state["bq_current"] = next_q
                    st.session_state["bq_phase"] = "monster_clear"
                else:
                    st.session_state["bq_current"] = next_q
                st.rerun()

    # ── フェーズ: 結果 ───────────────────────────────────────
    elif phase == "result":
        score   = st.session_state["bq_score"]
        hp      = st.session_state["bq_hp"]
        wrong   = st.session_state["bq_wrong"]
        total   = len(st.session_state["bq_questions"])
        cleared = hp > 0

        if not st.session_state.get("bq_exp_granted"):
            grant_exp(30 if cleared else 10)
            st.session_state["bq_exp_granted"] = True

        if cleared:
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#dcfce7,#bbf7d0);
                                border:2px solid #22c55e;border-radius:16px;
                                padding:28px;text-align:center;margin:12px 0;">
                    <div style="font-size:3em;">🏆</div>
                    <div style="font-size:1.8em;font-weight:bold;color:#15803d;margin:8px 0;">
                        4体全員撃破！クリア！
                    </div>
                    <div style="font-size:1.1em;color:#166534;">{total}問中 {score}問正解！</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.balloons()
        else:
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#fee2e2,#fecaca);
                                border:2px solid #ef4444;border-radius:16px;
                                padding:28px;text-align:center;margin:12px 0;">
                    <div style="font-size:3em;">💀</div>
                    <div style="font-size:1.8em;font-weight:bold;color:#b91c1c;margin:8px 0;">ゲームオーバー</div>
                    <div style="font-size:1.1em;color:#991b1b;">HPがなくなりました… {total}問中 {score}問正解</div>
                </div>""",
                unsafe_allow_html=True,
            )

        if wrong:
            st.markdown("---")
            st.subheader(f"📝 間違えた単語（{len(wrong)}語）")
            for w in wrong:
                st.markdown(
                    f"""<div style="background:#fff;border:1px solid #fca5a5;border-radius:8px;
                                    padding:12px 16px;margin:6px 0;">
                        <b style="color:#1e3a8a;font-size:1.1em;">{w['word']}</b>
                        <span style="color:#64748b;margin-left:12px;">{w['definition']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.success("全問正解！パーフェクト！🎉")

        st.markdown("---")
        if st.button("🔄 もう一度チャレンジ", type="primary", use_container_width=True):
            _reset_battle()
            st.rerun()


with tab_battle:
    _battle_quiz_ui()
