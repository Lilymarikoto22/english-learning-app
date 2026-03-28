from utils.web_search import search_bbc_news

results = search_bbc_news("Today's world economic news")
print(f"件数: {len(results)}")
for r in results:
    print(r["url"])
    print(r["title"])
    print()
