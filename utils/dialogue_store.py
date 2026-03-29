from utils.supabase_client import get_client


def save_dialogue(data: dict, genre: str) -> None:
    sb = get_client()
    sb.table("dialogues").insert({
        "data": data,
        "genre": genre,
    }).execute()


def get_all_dialogues() -> list[dict]:
    sb = get_client()
    res = sb.table("dialogues").select("*").order("saved_at", desc=True).execute()
    rows = res.data or []
    result = []
    for r in rows:
        item = r.get("data", {})
        item["genre"] = r.get("genre", "")
        saved_at = r.get("saved_at", "")
        item["saved_at"] = saved_at[:16].replace("T", " ") if saved_at else ""
        item["_id"] = r["id"]
        result.append(item)
    return result


def delete_dialogue(index: int) -> None:
    dialogues = get_all_dialogues()
    if 0 <= index < len(dialogues):
        get_client().table("dialogues").delete().eq("id", dialogues[index]["_id"]).execute()
