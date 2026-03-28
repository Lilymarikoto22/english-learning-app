import json
import os
from datetime import date

VOCAB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "vocabulary.json")


def _load() -> list[dict]:
    if not os.path.exists(VOCAB_FILE):
        return []
    with open(VOCAB_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(words: list[dict]) -> None:
    os.makedirs(os.path.dirname(VOCAB_FILE), exist_ok=True)
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


def get_all_words() -> list[dict]:
    return _load()


def add_word(word: str, definition: str) -> None:
    words = _load()
    words.append({
        "word": word.strip(),
        "definition": definition.strip(),
        "added": str(date.today()),
        "review_count": 0,
    })
    _save(words)


def update_review_count(index: int, increment: int) -> None:
    words = _load()
    if 0 <= index < len(words):
        words[index]["review_count"] = max(0, words[index]["review_count"] + increment)
        _save(words)


def delete_word(index: int) -> None:
    words = _load()
    if 0 <= index < len(words):
        words.pop(index)
        _save(words)
