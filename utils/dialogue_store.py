import json
import os
from datetime import datetime

DIALOGUE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "dialogues.json")


def _load() -> list[dict]:
    if not os.path.exists(DIALOGUE_FILE):
        return []
    with open(DIALOGUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(DIALOGUE_FILE), exist_ok=True)
    with open(DIALOGUE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def save_dialogue(data: dict, genre: str) -> None:
    items = _load()
    items.insert(0, {**data, "genre": genre, "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    _save(items)


def get_all_dialogues() -> list[dict]:
    return _load()


def delete_dialogue(index: int) -> None:
    items = _load()
    if 0 <= index < len(items):
        items.pop(index)
        _save(items)
