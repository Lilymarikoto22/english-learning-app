from datetime import date
from utils.supabase_client import get_client


def get_all_words() -> list[dict]:
    sb = get_client()
    res = sb.table("vocabulary").select("*").order("created_at", desc=False).execute()
    return res.data or []


def add_word(word: str, definition: str = "") -> None:
    sb = get_client()
    sb.table("vocabulary").insert({
        "word": word.strip(),
        "definition": definition.strip(),
        "review_count": 0,
    }).execute()


def update_review_count(index: int, increment: int) -> None:
    words = get_all_words()
    if 0 <= index < len(words):
        w = words[index]
        new_count = max(0, w.get("review_count", 0) + increment)
        get_client().table("vocabulary").update({"review_count": new_count}).eq("id", w["id"]).execute()


def delete_word(index: int) -> None:
    words = get_all_words()
    if 0 <= index < len(words):
        get_client().table("vocabulary").delete().eq("id", words[index]["id"]).execute()
