# 毎日自動実行するダイアログ事前生成スクリプト。
# 全ジャンル x 1本ずつ生成してアーカイブに保存する。

import sys
import os

# プロジェクトルートを import パスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# .env を読み込む
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from utils.claude_client import generate_dialogue
from utils.dialogue_store import save_dialogue

GENRES = {
    "🎲 Random":            "everyday",
    "💼 Business":          "business",
    "✈️ Travel":            "travel",
    "💬 Opinions":          "opinions",
    "😊 Feelings":          "feelings",
    "🗓️ Social situations": "social",
}

def main():
    print("=== Daily dialogue generation start ===")
    success = 0
    for label, genre in GENRES.items():
        try:
            print(f"Generating: {label} ...", end=" ", flush=True)
            data = generate_dialogue(genre=genre)
            save_dialogue(data, genre=label)
            print(f"OK  [{data['phrase']}]")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
    print(f"=== Done: {success}/{len(GENRES)} generated ===")

if __name__ == "__main__":
    main()
