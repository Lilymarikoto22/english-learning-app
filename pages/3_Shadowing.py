import os
import streamlit as st
from utils.claude_client import generate_shadowing_article, extract_business_vocab, translate_article, get_api_key
from utils.tts import generate_audio
from utils.article_store import save_article, get_all_articles, delete_article
from utils.web_search import search_bbc_news, search_ted_talks
from utils.vocab_store import add_word
from utils.streak_store import record_activity
from utils.pet_store import grant_exp, show_pet_notifications

st.set_page_config(page_title="Shadowing", page_icon="🗣️", layout="centered")
record_activity()
show_pet_notifications()

col_t, col_i = st.columns([4, 1])
with col_t:
    st.title("🗣️ Shadowing Practice")
    st.markdown("BBC 風のニュース記事を聴きながら、一緒に声に出して練習しましょう。")
with col_i:
    st.image("assets/study_woman_headphone.png", width=120)
st.markdown("---")

# APIキーチェック
try:
    get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()


def show_sources(sources: list[dict], source_type: str = "bbc") -> None:
    """ソース記事一覧を表示する。"""
    if not sources:
        return
    label = "🎤 ベースにした TED トーク" if source_type == "ted" else "📰 ベースにした BBC News 記事"
    with st.expander(label):
        for s in sources:
            st.markdown(f"- [{s['title']}]({s['url']})　<small>{s['date']}</small>", unsafe_allow_html=True)
            if s.get("body"):
                st.caption(s["body"][:150] + "…")


def show_article_player(article: dict, key_prefix: str = "") -> None:
    """記事表示と音声プレーヤーを描画する共通関数。key_prefix でキーの衝突を防ぐ。"""
    p = key_prefix  # 短縮形
    show_sources(article.get("sources", []), source_type=article.get("source_type", "bbc"))
    st.markdown(f"### {article['title']}")
    st.markdown(
        f"""
        <div style="
            background: #eff6ff;
            color: #1e293b;
            border-left: 4px solid #2563eb;
            padding: 16px 20px;
            border-radius: 4px;
            line-height: 1.9;
            font-size: 1.05em;
        ">
            {article['text'].replace(chr(10), '<br>')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    word_count = len(article["text"].split())
    st.caption(f"約 {word_count} 語 / 目安：約 {word_count // 130 + 1}〜{word_count // 120 + 1} 分")

    # 参考和訳
    trans_key = f"trans_{p}"
    if st.button("🇯🇵 参考和訳を表示", key=f"trans_btn_{p}"):
        with st.spinner("翻訳中..."):
            try:
                st.session_state[trans_key] = translate_article(article["text"])
            except Exception as e:
                st.error(f"翻訳に失敗しました: {e}")

    if trans_key in st.session_state:
        with st.expander("参考和訳", expanded=True):
            st.markdown(st.session_state[trans_key])

    st.markdown("---")
    st.subheader("音声を生成して練習する")

    speed = st.select_slider(
        "再生速度",
        options=[0.75, 1.0, 1.25, 1.5],
        value=1.0,
        format_func=lambda x: f"{x}x",
        key=f"speed_{p}",
    )

    audio_key = f"audio_{p}"
    speed_key = f"speed_cache_{p}"

    speed_changed = st.session_state.get(speed_key) != speed
    if speed_changed:
        if st.button("🔊 この速度で音声を再生成", type="primary", key=f"gen_{p}"):
            with st.spinner("音声を生成中..."):
                try:
                    audio_bytes = generate_audio(article["text"], speed=speed)
                    st.session_state[audio_key] = audio_bytes
                    st.session_state[speed_key] = speed
                    st.rerun()
                except Exception as e:
                    st.error(f"音声の生成に失敗しました: {e}")

    if audio_key in st.session_state and st.session_state[audio_key]:
        st.audio(st.session_state[audio_key], format="audio/mpeg")

        st.markdown("""
        **シャドウイングのやり方：**
        1. まず**通しで1回聴いて**内容をつかむ
        2. **0.75x のゆっくりペース**で一緒に声に出す
        3. 慣れたら **1.0x → 1.25x** と速度を上げる
        """)

    # ビジネス単語抽出セクション
    st.markdown("---")
    st.subheader("💼 ビジネス重要単語")
    vocab_key = f"biz_vocab_{p}"

    if st.button("📖 この記事からビジネス単語を抽出", key=f"extract_{p}"):
        with st.spinner("Claude がビジネス単語を抽出中..."):
            try:
                words = extract_business_vocab(article["text"])
                st.session_state[vocab_key] = words
            except Exception as e:
                st.error(f"抽出に失敗しました: {e}")

    if vocab_key in st.session_state:
        words = st.session_state[vocab_key]
        selected = []

        for i, w in enumerate(words):
            col_check, col_content = st.columns([1, 11])
            with col_check:
                checked = st.checkbox("", value=True, key=f"biz_{p}_{i}")
            with col_content:
                st.markdown(
                    f"**{w['word']}**　{w['definition']}  \n"
                    f"<span style='color:#888;font-size:0.9em;'>例：{w['example']}</span>",
                    unsafe_allow_html=True,
                )
            if checked:
                selected.append(w)

        st.markdown("")
        if st.button(
            f"✅ チェックした {len(selected)} 語を単語帳に追加",
            type="primary",
            key=f"add_biz_{p}",
            disabled=not selected,
        ):
            for w in selected:
                add_word(w["word"], f"{w['definition']} / {w['example']}")
            st.success(f"{len(selected)} 語を単語帳に追加しました！")
            del st.session_state[vocab_key]
            st.rerun()


# ---- タブ ----
tab_new, tab_archive = st.tabs(["📝 新しい記事を生成", "📂 アーカイブ"])


# ---- タブ1: 新規生成 ----
with tab_new:
    st.subheader("Step 1：トピックを選ぶ")

    TOPIC_POOL = [
        "Climate change and renewable energy",
        "Artificial intelligence in everyday life",
        "Global travel and tourism recovery",
        "Health and wellbeing in modern society",
        "Space exploration and new discoveries",
        "The future of remote work",
        "Biodiversity and wildlife conservation",
        "The global semiconductor shortage",
        "Electric vehicles and the future of transport",
        "Social media and mental health",
        "The rise of sustainable fashion",
        "Ageing populations and healthcare challenges",
        "Cybersecurity threats in the digital age",
        "Food security and global agriculture",
        "The future of higher education",
        "Immigration and cultural diversity",
        "Water scarcity around the world",
        "The gig economy and workers' rights",
        "Urbanisation and smart cities",
        "The impact of inflation on daily life",
        "Geopolitics and global trade tensions",
        "Quantum computing breakthroughs",
        "Women in leadership roles",
        "The future of healthcare and telemedicine",
        "Plastic pollution and the oceans",
        "Nuclear energy as a climate solution",
        "The global housing crisis",
        "Remote learning and education technology",
        "The ethics of genetic engineering",
        "Tourism and its impact on local communities",
        "The rise of podcasts and digital media",
        "Cryptocurrency and the future of money",
        "Mental health awareness in the workplace",
        "The impact of streaming on the music industry",
        "Fast food culture and global obesity",
        "The space tourism industry",
        "Automation and the future of manufacturing jobs",
        "Microplastics and human health",
        "The growing influence of K-pop and Korean culture",
        "Sleep science and its impact on productivity",
        "The role of forests in fighting climate change",
        "The boom in online shopping and its consequences",
        "Drug-resistant bacteria and the antibiotic crisis",
        "The future of newspapers and journalism",
        "Youth activism and climate protests",
    ]

    FIXED_TOPICS = ["Today's world economic news"]

    # ページを開いたときだけランダム選出（Streamlit の再レンダリングでは変わらない）
    if "topic_choices" not in st.session_state:
        import random
        sampled = random.sample(TOPIC_POOL, 6)
        st.session_state["topic_choices"] = FIXED_TOPICS + sampled

    col_topic, col_refresh = st.columns([5, 1])
    with col_topic:
        options = st.session_state["topic_choices"] + ["カスタム入力"]
        selected = st.selectbox("トピックを選ぶ（または自分で入力）", options)
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔀", help="候補をシャッフル"):
            import random
            st.session_state["topic_choices"] = FIXED_TOPICS + random.sample(TOPIC_POOL, 6)
            st.rerun()
    if selected == "カスタム入力":
        topic = st.text_input("トピックを英語で入力", placeholder="例: the history of tea in Britain")
    else:
        topic = selected

    st.markdown("---")
    st.subheader("Step 2：ソースを選ぶ")

    source_choice = st.radio(
        "記事のソース",
        ["📰 BBC News", "🎤 TED Talks"],
        horizontal=True,
        help="BBC News はニュース記事風、TED Talks はスピーチ・プレゼン風の英語になります",
    )
    source_type = "ted" if "TED" in source_choice else "bbc"

    st.markdown("---")
    st.subheader("Step 3：記事を生成する")

    if st.button("📝 記事を生成", type="primary", disabled=not topic):
        source_label = "TED Talks" if source_type == "ted" else "BBC News"
        sources = []

        with st.status("記事を準備しています...", expanded=True) as status:
            st.write(f"📡 Step 1／3　{source_label} を検索中...")
            try:
                if source_type == "ted":
                    sources = search_ted_talks(topic, max_results=4)
                else:
                    sources = search_bbc_news(topic, max_results=4)
                if sources:
                    st.write(f"✅ {len(sources)} 件の記事が見つかりました")
                else:
                    st.write("⚠️ 記事が見つかりませんでした。Claude の知識で生成します")
            except Exception as e:
                st.write(f"⚠️ 検索エラー: {e}")

            st.write("✍️ Step 2／3　Claude が記事を執筆中...（10〜20秒）")
            try:
                article = generate_shadowing_article(topic, source_articles=sources or None, source_type=source_type)
                article["sources"] = sources
                article["source_type"] = source_type
                st.session_state["current_article"] = article
                st.session_state["current_topic"] = topic
                st.session_state["article_saved"] = False
                st.write(f"✅ 記事「{article['title']}」完成！")
            except Exception as e:
                st.error(f"記事の生成に失敗しました: {e}")
                st.stop()

            st.write("🔊 Step 3／3　音声を生成中...（10〜20秒）")
            audio_key = f"audio_{article['title'][:20]}"
            try:
                audio_bytes = generate_audio(article["text"], speed=1.0)
                st.session_state[audio_key] = audio_bytes
                st.session_state[f"speed_cache_{article['title'][:20]}"] = 1.0
                st.write("✅ 音声の準備ができました！")
            except Exception as e:
                st.write(f"⚠️ 音声の自動生成に失敗しました（後で手動生成できます）: {e}")

            status.update(label="✅ 完成！記事と音声の準備ができました", state="complete")

    if "current_article" in st.session_state:
        article = st.session_state["current_article"]

        # アーカイブ保存ボタン
        if not st.session_state.get("article_saved", False):
            if st.button("💾 この記事をアーカイブに保存"):
                save_article(article["title"], article["text"], st.session_state.get("current_topic", ""), sources=article.get("sources", []))
                st.session_state["article_saved"] = True
                st.success("アーカイブに保存しました！")
        else:
            st.success("✅ アーカイブに保存済み")

        st.markdown("---")
        show_article_player(article, key_prefix="new")

        # ── EXP ──
        st.markdown("---")
        _exp_key = f"_exp_shadow_{article['title'][:20]}"
        if not st.session_state.get(_exp_key):
            if st.button("✅ シャドウイング完了！(+30pt)", type="primary", use_container_width=True):
                grant_exp(30)
                st.session_state[_exp_key] = True
                st.rerun()
        else:
            st.success("🐾 ペットに +30pt あげました！")


# ---- タブ2: アーカイブ ----
with tab_archive:
    articles = get_all_articles()

    if not articles:
        st.info("まだ保存された記事がありません。記事を生成して「アーカイブに保存」ボタンを押してください。")
    else:
        st.markdown(f"**{len(articles)} 件の記事が保存されています**")

        for i, a in enumerate(articles):
            label = f"**{a['title']}**　— {a['saved_at']}"
            with st.expander(label):
                show_article_player(a, key_prefix=f"arc_{i}")
                st.markdown("---")
                if st.button("🗑️ 削除", key=f"del_article_{i}"):
                    delete_article(i)
                    st.rerun()
