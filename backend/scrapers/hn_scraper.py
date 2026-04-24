import requests

def run():
    # HackerNews Algolia API — completely free, no auth
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": "Ask HN: is there an app that",
        "tags": "ask_hn",
        "numericFilters": "points>50",
        "hitsPerPage": 100
    }

    posts = []
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        for hit in data.get("hits", []):
            posts.append({
                "id": f"hn_{hit['objectID']}",
                "source": "hn",
                "content": f"{hit.get('title', '')}\n{hit.get('story_text', '') or ''}",
                "metadata": {"points": hit.get("points", 0), "url": hit.get("url", "")}
            })
    except Exception as e:
        print(f"HN scraper error: {e}")

    print(f"HackerNews: collected {len(posts)} posts")
    return posts
