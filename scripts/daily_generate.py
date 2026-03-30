# 毎日自動実行するダイアログ事前生成スクリプト。
# 全ジャンル x 1本ずつ生成してアーカイブに保存する。

import sys
import os

# Windows コンソールの文字化け対策
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# プロジェクトルートを import パスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# .env を読み込む
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"), override=True)

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
    log_path = os.path.join(project_root, "scripts", "daily_generate.log")
    with open(log_path, "a", encoding="utf-8") as log:
        from datetime import datetime
        log.write(f"\n=== {datetime.now()} ===\n")
        log.write(f"project_root: {project_root}\n")
        log.write(f"ANTHROPIC_API_KEY: {'set' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}\n")
        log.write(f"SUPABASE_KEY: {'set' if os.getenv('SUPABASE_KEY') else 'NOT SET'}\n")

        success = 0
        for label, genre in GENRES.items():
            try:
                log.write(f"Generating: {label} ... ")
                data = generate_dialogue(genre=genre)
                save_dialogue(data, genre=label)
                log.write(f"OK [{data['phrase']}]\n")
                success += 1
            except Exception as e:
                log.write(f"FAILED: {e}\n")
        log.write(f"Done: {success}/{len(GENRES)}\n")

if __name__ == "__main__":
    main()
