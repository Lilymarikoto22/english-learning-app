import os
import streamlit as st
from utils.claude_client import generate_dialogue, translate_dialogue, get_api_key
from utils.tts import generate_dialogue_audio
from utils.vocab_store import add_word
from utils.dialogue_store import save_dialogue, get_all_dialogues, delete_dialogue
from utils.streak_store import record_activity

st.set_page_config(page_title="Dialogue", page_icon="🎭", layout="centered")
record_activity()

col_t, col_i = st.columns([4, 1])
with col_t:
    st.title("🎭 Phrase & Dialogue")
    st.markdown("Learn a natural English phrase through a short British story.")
with col_i:
    st.image("assets/animal_penguin_music_band.png", width=120)
st.markdown("---")

try:
    get_api_key()
except ValueError as e:
    st.error(str(e))
    st.stop()

GENRES = {
    "🎲 Random":            "everyday",
    "💼 Business":          "business",
    "✈️ Travel":            "travel",
    "💬 Opinions":          "opinions",
    "😊 Feelings":          "feelings",
    "🗓️ Social situations": "social",
}

tab_new, tab_archive = st.tabs(["🎭 New dialogue", "📂 Archive"])


def show_dialogue(data: dict, key_prefix: str = "") -> None:
    p = key_prefix

    # ---- フレーズカード ----
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #dbeafe, #eff6ff);
            color: #1e293b;
            border-radius: 12px;
            border: 1px solid #93c5fd;
            padding: 24px 28px;
            margin: 8px 0 16px 0;
            box-shadow: 0 2px 12px rgba(37,99,235,0.1);
        ">
            <div style="font-size:0.85em; color:#2563eb; letter-spacing:1px; font-weight:600;">PHRASE OF THE DAY</div>
            <div style="font-size:2em; font-weight:bold; color:#1e3a8a; margin: 8px 0;">"{data['phrase']}"</div>
            <div style="font-size:1em; color:#334155; margin-bottom:12px;">{data['explanation']}</div>
            <div style="font-size:0.9em; color:#475569;">
                <b>When to use:</b> {data['when_to_use']}
            </div>
            <div style="font-size:0.85em; color:#64748b; margin-top:10px;">
                <b>Similar expressions:</b> {" · ".join(data.get('similar_expressions', []))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("📚 Save phrase to Vocabulary", key=f"{p}save_vocab"):
        add_word(
            data["phrase"],
            f"{data['explanation']} / When to use: {data['when_to_use']}",
        )
        st.success("Saved to Vocabulary!")

    st.markdown("---")
    st.subheader("Dialogue")

    for i, line in enumerate(data["dialogue"]):
        is_female = line["speaker"] == "F"
        name = line["name"]
        text = line["line"]

        if is_female:
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; margin:8px 0;">
                    <div style="
                        background:#dcfce7; color:#14532d;
                        border-radius:4px 16px 16px 16px;
                        padding:10px 14px; max-width:80%;
                        border: 1px solid #86efac;
                    ">
                        <div style="font-size:0.75em; color:#16a34a; margin-bottom:4px; font-weight:600;">{name}</div>
                        <div>{text}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-end; margin:8px 0;">
                    <div style="
                        background:#dbeafe; color:#1e3a8a;
                        border-radius:16px 4px 16px 16px;
                        padding:10px 14px; max-width:80%;
                        text-align:right;
                        border: 1px solid #93c5fd;
                    ">
                        <div style="font-size:0.75em; color:#2563eb; margin-bottom:4px; font-weight:600;">{name}</div>
                        <div>{text}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- 和訳 ----
    trans_key = f"{p}translation"
    if st.button("🇯🇵 Show Japanese translation", key=f"{p}btn_translate"):
        with st.spinner("Translating..."):
            try:
                st.session_state[trans_key] = translate_dialogue(data)
            except Exception as e:
                st.error(f"Translation failed: {e}")

    if st.session_state.get(trans_key):
        with st.expander("Japanese translation", expanded=True):
            st.markdown(st.session_state[trans_key])

    st.markdown("---")

    # ---- 音声生成 ----
    speed = st.select_slider(
        "Speed",
        options=[0.75, 1.0, 1.25],
        value=1.0,
        format_func=lambda x: f"{x}x",
        key=f"{p}speed",
    )

    audio_key = f"{p}audio"
    audio_speed_key = f"{p}audio_speed"

    if st.button("🔊 Generate audio", type="primary", key=f"{p}btn_audio"):
        with st.spinner("Generating two-voice audio... (may take 20–30 seconds)"):
            try:
                lines = [{"speaker": l["speaker"], "line": l["line"]} for l in data["dialogue"]]
                path = generate_dialogue_audio(lines, speed=speed)
                st.session_state[audio_key] = path
                st.session_state[audio_speed_key] = speed
            except Exception as e:
                st.error(f"Audio generation failed: {e}")

    if st.session_state.get(audio_key) and os.path.exists(st.session_state[audio_key]):
        if st.session_state.get(audio_speed_key) != speed:
            st.info("Speed changed — press 'Generate audio' again.")
        with open(st.session_state[audio_key], "rb") as f:
            st.audio(f.read(), format="audio/mp3")
        st.caption("🟢 Sophie (female) · 🔵 James (male) — both in British English")


# ==============================
# Tab 1: New dialogue
# ==============================
with tab_new:
    col1, col2 = st.columns([3, 1])
    with col1:
        genre_label = st.selectbox("Genre", list(GENRES.keys()))
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("▶ Generate", type="primary", use_container_width=True)

    if generate_btn:
        with st.spinner("Creating dialogue..."):
            try:
                data = generate_dialogue(genre=GENRES[genre_label])
                st.session_state["dialogue_data"] = data
                st.session_state["dialogue_genre"] = genre_label
                # clear previous state for this view
                st.session_state.pop("new_translation", None)
                st.session_state.pop("new_audio", None)
            except Exception as e:
                st.error(f"Failed to generate: {e}")

    if "dialogue_data" not in st.session_state:
        st.info("Select a genre and press **Generate** to start.")
        st.stop()

    data = st.session_state["dialogue_data"]

    show_dialogue(data, key_prefix="new_")

    st.markdown("---")
    if st.button("💾 Save to Archive", key="new_save_archive"):
        save_dialogue(data, genre=st.session_state.get("dialogue_genre", ""))
        st.success("Saved to Archive!")


# ==============================
# Tab 2: Archive
# ==============================
with tab_archive:
    dialogues = get_all_dialogues()

    if not dialogues:
        st.info("No saved dialogues yet. Generate one and press **Save to Archive**.")
    else:
        st.markdown(f"**{len(dialogues)} dialogue(s) saved**")
        for i, item in enumerate(dialogues):
            label = f"**{item['phrase']}** — {item.get('genre', '')}  ·  {item.get('saved_at', '')}"
            with st.expander(label):
                show_dialogue(item, key_prefix=f"arch{i}_")

                st.markdown("---")
                if st.button("🗑️ Delete", key=f"arch{i}_delete"):
                    delete_dialogue(i)
                    st.success("Deleted.")
                    st.rerun()
