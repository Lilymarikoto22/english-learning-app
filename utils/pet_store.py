"""Study Pet の EXP・ステージ管理。"""
from datetime import date
from utils.supabase_client import get_client

DAILY_CAP = 100  # 1日の EXP 上限

# (stage, 累積EXP下限)
STAGE_THRESHOLDS = [(1, 0), (2, 100), (3, 300), (4, 600), (5, 1000), (6, 1500)]

STAGE_INFO = {
    1: {"name": "たまご",       "emoji": "🥚"},
    2: {"name": "あかちゃん",   "emoji": "🐣"},
    3: {"name": "こねこ",       "emoji": "🐱"},
    4: {"name": "ねこ",         "emoji": "😺"},
    5: {"name": "おとなねこ",   "emoji": "😸"},
    6: {"name": "まんかいねこ", "emoji": "🐈"},
}


def _compute_stage(total_exp: int) -> int:
    stage = 1
    for s, threshold in STAGE_THRESHOLDS:
        if total_exp >= threshold:
            stage = s
    return stage


def next_stage_exp(stage: int):
    """次のステージに必要な累積EXPを返す。最大ステージなら None。"""
    for s, threshold in STAGE_THRESHOLDS:
        if s == stage + 1:
            return threshold
    return None


def get_pet() -> dict:
    """ペットデータを取得。新日付なら today_exp をリセット。"""
    sb = get_client()
    res = sb.table("pet").select("*").eq("id", 1).execute()
    if not res.data:
        default = {
            "id": 1, "stage": 1, "total_exp": 0,
            "today_exp": 0, "last_exp_date": "", "mood": "happy",
        }
        sb.table("pet").insert(default).execute()
        return default

    pet = res.data[0]
    today = str(date.today())

    if pet.get("last_exp_date", "") != today and pet.get("today_exp", 0) > 0:
        sb.table("pet").update({"today_exp": 0, "last_exp_date": today}).eq("id", 1).execute()
        pet["today_exp"] = 0
        pet["last_exp_date"] = today

    return pet


def add_exp(points: int) -> dict:
    """EXPを加算する（daily cap 以内）。結果 dict を返す。"""
    pet = get_pet()
    today = str(date.today())

    remaining = max(0, DAILY_CAP - pet.get("today_exp", 0))
    actual_gain = min(points, remaining)

    if actual_gain <= 0:
        return {
            "gained": 0,
            "today_exp": pet.get("today_exp", 0),
            "total_exp": pet.get("total_exp", 0),
            "stage": pet.get("stage", 1),
            "leveled_up": False,
            "is_full": True,
        }

    old_stage = _compute_stage(pet.get("total_exp", 0))
    new_today = pet.get("today_exp", 0) + actual_gain
    new_total = pet.get("total_exp", 0) + actual_gain
    new_stage = _compute_stage(new_total)
    leveled_up = new_stage > old_stage

    sb = get_client()
    sb.table("pet").update({
        "today_exp": new_today,
        "total_exp": new_total,
        "stage": new_stage,
        "last_exp_date": today,
        "mood": "excited" if leveled_up else "happy",
    }).eq("id", 1).execute()

    return {
        "gained": actual_gain,
        "today_exp": new_today,
        "total_exp": new_total,
        "stage": new_stage,
        "leveled_up": leveled_up,
        "is_full": new_today >= DAILY_CAP,
    }


def grant_exp(points: int) -> None:
    """EXP 加算し、Streamlit session_state に通知をセットする。"""
    import streamlit as st
    result = add_exp(points)
    if result["leveled_up"]:
        st.session_state["_pet_balloons"] = True
        st.session_state["_pet_toast"] = (
            f"🎉 ペットが進化した！ → {STAGE_INFO[result['stage']]['emoji']} {STAGE_INFO[result['stage']]['name']}"
        )
    elif result["gained"] > 0:
        st.session_state["_pet_toast"] = f"🐱 +{result['gained']}pt！ペットが喜んでいる"
    else:
        st.session_state["_pet_toast"] = "🌙 今日はおなかいっぱい！また明日ね"


def show_pet_notifications() -> None:
    """各ページ上部で呼ぶ。toast / balloons を表示する。"""
    import streamlit as st
    if "_pet_toast" in st.session_state:
        st.toast(st.session_state.pop("_pet_toast"), icon="🐾")
    if st.session_state.pop("_pet_balloons", False):
        st.balloons()
