# 毎日自動実行するシャドウイング記事の事前生成スクリプト。
# トピックをランダムに選んでBBCニュースから記事を生成してアーカイブに保存する。

import sys
import os
import random

# Windows コンソールの文字化け対策
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# プロジェクトルートを import パスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"), override=True)

from utils.claude_client import generate_shadowing_article
from utils.web_search import search_bbc_news
from utils.article_store import save_article

TOPIC_POOL = [
    "Climate change and renewable energy",
    "Artificial intelligence in everyday life",
    "Global travel and tourism recovery",
    "Health and wellbeing in modern society",
    "Space exploration and new discoveries",
    "The future of remote work",
    "Biodiversity and wildlife conservation",
    "The global semiconductor shortage",
    "Electric vehicles and the future of transport",
    "Social media and mental health",
    "The rise of sustainable fashion",
    "Ageing populations and healthcare challenges",
    "Cybersecurity threats in the digital age",
    "Food security and global agriculture",
    "The future of higher education",
    "Water scarcity around the world",
    "The gig economy and workers' rights",
    "Urbanisation and smart cities",
    "The impact of inflation on daily life",
    "Geopolitics and global trade tensions",
    "Quantum computing breakthroughs",
    "Women in leadership roles",
    "The future of healthcare and telemedicine",
    "Plastic pollution and the oceans",
    "Nuclear energy as a climate solution",
    "The global housing crisis",
    "The ethics of genetic engineering",
    "Cryptocurrency and the future of money",
    "Mental health awareness in the workplace",
    "Microplastics and human health",
    "Sleep science and its impact on productivity",
    "The role of forests in fighting climate change",
    "Drug-resistant bacteria and the antibiotic crisis",
    "Youth activism and climate protests",
    "Today's world economic news",
]

ARTICLES_PER_DAY = 3


def main():
    from datetime import datetime
    log_path = os.path.join(project_root, "scripts", "daily_shadowing.log")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n=== {datetime.now()} ===\n")
        log.write(f"ANTHROPIC_API_KEY: {'set' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}\n")
        log.write(f"SUPABASE_KEY: {'set' if os.getenv('SUPABASE_KEY') else 'NOT SET'}\n")

        topics = random.sample(TOPIC_POOL, ARTICLES_PER_DAY)
        success = 0

        for topic in topics:
            try:
                log.write(f"Generating: {topic} ... ")
                sources = search_bbc_news(topic, max_results=4)
                article = generate_shadowing_article(
                    topic,
                    source_articles=sources or None,
                    source_type="bbc"
                )
                save_article(
                    article["title"],
                    article["text"],
                    topic,
                    sources=sources or []
                )
                log.write(f"OK [{article['title']}]\n")
                success += 1
            except Exception as e:
                log.write(f"FAILED: {e}\n")

        log.write(f"Done: {success}/{ARTICLES_PER_DAY}\n")


if __name__ == "__main__":
    main()
