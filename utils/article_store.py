from utils.supabase_client import get_client


def save_article(title: str, text: str, topic: str, sources: list[dict] | None = None) -> None:
    sb = get_client()
    sb.table("articles").insert({
        "title": title,
        "text": text,
        "topic": topic,
        "sources": sources or [],
    }).execute()


def get_all_articles() -> list[dict]:
    sb = get_client()
    res = sb.table("articles").select("*").order("saved_at", desc=True).execute()
    rows = res.data or []
    for r in rows:
        # saved_at を見やすい形式に変換
        if r.get("saved_at"):
            r["saved_at"] = r["saved_at"][:16].replace("T", " ")
    return rows


def delete_article(index: int) -> None:
    articles = get_all_articles()
    if 0 <= index < len(articles):
        get_client().table("articles").delete().eq("id", articles[index]["id"]).execute()
