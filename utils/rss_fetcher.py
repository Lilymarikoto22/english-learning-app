import feedparser
import streamlit as st

BBC_RSS_URL = "https://www.bbc.co.uk/programmes/p02pc9zn/episodes/downloads.rss"


@st.cache_data(ttl=3600)  # 1時間キャッシュ
def fetch_episodes(max_episodes: int = 10) -> list[dict]:
    """BBC 6 Minute English のエピソード一覧を取得する。

    Returns:
        [{"title": str, "audio_url": str, "published": str, "summary": str}, ...]
    """
    feed = feedparser.parse(BBC_RSS_URL)

    episodes = []
    for entry in feed.entries[:max_episodes]:
        audio_url = ""
        for enclosure in entry.get("enclosures", []):
            if "audio" in enclosure.get("type", ""):
                audio_url = enclosure.get("href", "")
                break

        if not audio_url:
            continue

        episodes.append({
            "title": entry.get("title", "Unknown"),
            "audio_url": audio_url,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
        })

    return episodes
