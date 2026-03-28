import re
import feedparser

TED_FEED_URL = "https://feeds.feedburner.com/TEDTalks_audio"
_ted_cache: list[dict] = []


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _fetch_ted(limit: int = 100) -> list[dict]:
    global _ted_cache
    if _ted_cache:
        return _ted_cache
    feed = feedparser.parse(TED_FEED_URL)
    results = []
    for entry in feed.entries[:limit]:
        results.append({
            "title": entry.get("title", ""),
            "url":   entry.get("link", ""),
            "body":  _strip_html(entry.get("summary", "")),
            "date":  entry.get("published", ""),
        })
    _ted_cache = results
    return results


def search_ted_talks(topic: str, max_results: int = 4) -> list[dict]:
    """TED RSS フィードからトピックに関連するトークを返す。

    Returns:
        [{"title": str, "url": str, "body": str, "date": str}, ...]
    """
    all_talks = _fetch_ted(limit=100)
    if not all_talks:
        return []

    keywords = re.sub(r"[^\w\s]", "", topic.lower()).split()
    keywords = [w for w in keywords if len(w) > 3]

    scored = sorted(all_talks, key=lambda a: _score(a, keywords), reverse=True)
    result = [a for a in scored if _score(a, keywords) > 0]
    if not result:
        result = all_talks  # マッチなければ最新トークを返す

    return result[:max_results]

# BBC RSS フィード一覧
BBC_FEEDS = {
    "business":    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "world":       "https://feeds.bbci.co.uk/news/world/rss.xml",
    "technology":  "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "science":     "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "health":      "https://feeds.bbci.co.uk/news/health/rss.xml",
    "education":   "https://feeds.bbci.co.uk/news/education/rss.xml",
}

# トピック → 使用するフィードカテゴリのマッピング
TOPIC_FEED_MAP = {
    "Today's world economic news": ["business", "world"],
    "Geopolitics and global trade tensions": ["world", "business"],
    "The global semiconductor shortage": ["technology", "business"],
    "Cryptocurrency and the future of money": ["technology", "business"],
    "The impact of inflation on daily life": ["business", "world"],
    "Quantum computing breakthroughs": ["technology", "science"],
    "The future of healthcare and telemedicine": ["health", "technology"],
}

# キーワードで使用するフィードを推定する
_KEYWORD_FEED = [
    (["economy", "trade", "market", "inflation", "gdp", "finance", "bank"],  ["business"]),
    (["ai", "artificial intelligence", "tech", "software", "digital", "cyber", "robot"], ["technology"]),
    (["climate", "environment", "biodiversity", "ocean", "forest", "carbon", "energy"],  ["science"]),
    (["health", "medicine", "disease", "hospital", "mental", "obesity"],                 ["health"]),
    (["education", "school", "university", "learning", "student"],                       ["education"]),
]


def _get_feed_categories(topic: str) -> list[str]:
    """トピックに合った BBC フィードカテゴリを返す。"""
    if topic in TOPIC_FEED_MAP:
        return TOPIC_FEED_MAP[topic]

    t = topic.lower()
    for keywords, categories in _KEYWORD_FEED:
        if any(kw in t for kw in keywords):
            return categories + ["world"]

    return ["world", "business"]


def _fetch_feed(category: str) -> list[dict]:
    """BBC RSS フィードを取得して記事リストを返す。"""
    url = BBC_FEEDS.get(category, BBC_FEEDS["world"])
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:20]:
        results.append({
            "title": entry.get("title", ""),
            "url":   entry.get("link", ""),
            "body":  entry.get("summary", ""),
            "date":  entry.get("published", ""),
        })
    return results


def _score(article: dict, keywords: list[str]) -> int:
    """記事のタイトル・本文にキーワードが何個含まれるか返す。"""
    text = (article["title"] + " " + article["body"]).lower()
    return sum(1 for kw in keywords if kw in text)


def search_bbc_news(topic: str, max_results: int = 4) -> list[dict]:
    """BBC RSS フィードからトピックに関連する最新記事を返す。

    Returns:
        [{"title": str, "url": str, "body": str, "date": str}, ...]
    """
    categories = _get_feed_categories(topic)

    # 複数フィードを取得して重複除去
    seen_urls = set()
    all_articles = []
    for cat in categories:
        for a in _fetch_feed(cat):
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                all_articles.append(a)

    if not all_articles:
        return []


    # キーワードで関連度スコアリング
    keywords = re.sub(r"[^\w\s]", "", topic.lower()).split()
    keywords = [w for w in keywords if len(w) > 3]  # 短い語を除外

    scored = sorted(all_articles, key=lambda a: _score(a, keywords), reverse=True)

    # スコア0の記事も含めてフィードの最新記事を返す（トピックが広い場合）
    result = [a for a in scored if _score(a, keywords) > 0]
    if not result:
        result = all_articles  # キーワードマッチなければフィード最新記事をそのまま使う

    return result[:max_results]
