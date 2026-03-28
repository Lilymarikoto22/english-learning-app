import json
import os
from datetime import datetime

ARTICLE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "articles.json")


def _load() -> list[dict]:
    if not os.path.exists(ARTICLE_FILE):
        return []
    with open(ARTICLE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(articles: list[dict]) -> None:
    os.makedirs(os.path.dirname(ARTICLE_FILE), exist_ok=True)
    with open(ARTICLE_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


def save_article(title: str, text: str, topic: str, sources: list[dict] | None = None) -> None:
    articles = _load()
    articles.insert(0, {
        "title": title,
        "text": text,
        "topic": topic,
        "sources": sources or [],
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _save(articles)


def get_all_articles() -> list[dict]:
    return _load()


def delete_article(index: int) -> None:
    articles = _load()
    if 0 <= index < len(articles):
        articles.pop(index)
        _save(articles)
