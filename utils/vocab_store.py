from utils.supabase_client import get_client


def _fetch_all(query) -> list[dict]:
    """ページネーションで全件取得する。"""
    all_data = []
    page = 1000
    offset = 0
    while True:
        res = query.range(offset, offset + page - 1).execute()
        if not res.data:
            break
        all_data.extend(res.data)
        if len(res.data) < page:
            break
        offset += page
    return all_data


def get_all_words() -> list[dict]:
    sb = get_client()
    return _fetch_all(sb.table("vocabulary").select("*").order("created_at", desc=False))


def get_words_by_level(level: str) -> list[dict]:
    sb = get_client()
    q = sb.table("vocabulary").select("*").order("created_at", desc=False)
    if level:
        q = q.eq("level", level)
    return _fetch_all(q)


def add_word(word: str, definition: str = "", level: str = "",
             pos: str = "", verb_type: str = "", pronunciation: str = "",
             toeic_target: str = "") -> None:
    sb = get_client()
    sb.table("vocabulary").insert({
        "word": word.strip(),
        "definition": definition.strip(),
        "review_count": 0,
        "level": level,
        "pos": pos.strip(),
        "verb_type": verb_type.strip(),
        "pronunciation": pronunciation.strip(),
        "toeic_target": toeic_target.strip(),
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
