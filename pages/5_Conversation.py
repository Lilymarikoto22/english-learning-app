import streamlit as st
from streamlit_mic_recorder import mic_recorder
from utils.claude_client import stream_conversation, transcribe_audio, extract_vocab_from_conversation, get_api_key
from utils.vocab_store import add_word
from utils.streak_store import record_activity
from utils.auth import require_password

st.set_page_config(page_title="Conversation", page_icon="💬", layout="centered")
require_password()
record_activity()

col_t, col_i = st.columns([4, 1])
with col_t:
    st.title("💬 Conversation Practice")
    st.markdown("Claude と英語で会話しましょう。文法ミスがあればやさしく教えてくれます。")
with col_i:
    st.image("assets/communication_hanashiai.png", width=120)
st.markdown("---")

# APIキーチェック
try:
    get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()

# 会話履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# トピック選択と会話リセット
col1, col2 = st.columns([3, 1])

with col1:
    topics = {
        "自由会話": None,
        "今日の出来事を話す": "Let's talk about what you did today. I'll ask you some questions!",
        "趣味について話す": "Tell me about your hobbies! What do you enjoy doing in your free time?",
        "旅行について話す": "Let's talk about travel! Have you been anywhere interesting recently, or is there somewhere you'd like to go?",
        "仕事・勉強について話す": "Tell me about your work or studies. What are you working on these days?",
        "好きな映画・音楽": "Let's chat about movies or music! What have you been watching or listening to lately?",
    }
    selected_topic = st.selectbox("話すトピックを選ぶ", list(topics.keys()))

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 リセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# トピックが選ばれたら最初のメッセージを自動送信
if selected_topic != "自由会話" and topics[selected_topic]:
    if not st.session_state.messages:
        opener = topics[selected_topic]
        st.session_state.messages.append({"role": "assistant", "content": opener})

st.markdown("---")

# 過去のメッセージを表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 音声入力
st.markdown("**🎤 音声入力**（ボタンを押して話してください）")
audio = mic_recorder(
    start_prompt="🎤 録音開始",
    stop_prompt="⏹️ 録音停止",
    just_once=True,
    key="mic",
)

if audio:
    with st.spinner("音声を文字起こし中..."):
        transcribed = transcribe_audio(audio["bytes"])
    if transcribed.strip():
        st.info(f"文字起こし結果: {transcribed}")
        user_input = transcribed
    else:
        st.warning("音声を認識できませんでした。もう一度試してください。")
        user_input = None
else:
    user_input = None

# テキスト入力（音声入力がない場合）
text_input = st.chat_input("またはテキストで入力... (例: I went to the park yesterday.)")
if text_input:
    user_input = text_input

if user_input:
    # ユーザーメッセージを追加・表示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Claude の返答をストリーミング表示
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # API に渡すメッセージ（session_state から role/content のみ抽出）
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        for chunk in stream_conversation(api_messages):
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 会話から単語抽出ボタン
if len(st.session_state.messages) >= 2:
    st.markdown("---")
    if st.button("📚 この会話から単語を単語帳に追加", use_container_width=True):
        with st.spinner("単語を抽出中..."):
            try:
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                words = extract_vocab_from_conversation(api_messages)
                if words:
                    for w in words:
                        add_word(w["word"], w["definition"],
                                 pos=w.get("pos", ""), verb_type=w.get("verb_type", ""),
                                 pronunciation=w.get("pronunciation", ""),
                                 toeic_target=w.get("toeic_target", ""))
                    st.success(f"✅ {len(words)} 語を単語帳に追加しました！")
                    for w in words:
                        pron = f" {w['pronunciation']}" if w.get("pronunciation") else ""
                        pos_info = " / ".join(p for p in [w.get("pos",""), w.get("verb_type","")] if p)
                        pos_str = f" ({pos_info})" if pos_info else ""
                        st.markdown(f"- **{w['word']}**{pron}{pos_str}: {w['definition']}")
                else:
                    st.info("抽出できる単語が見つかりませんでした。")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
