from pytrends.request import TrendReq
import time
from backend.config import settings

SEED_KEYWORDS = [
    "productivity app", "freelancer tool", "SaaS automation",
    "AI assistant", "remote work tool", "budget tracker app"
]

def run():
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
    except Exception as e:
        print(f"Failed to initialize pytrends: {e}")
        return []

    posts = []
    
    # Use user-defined target keywords if available, otherwise default seeds
    keywords_to_use = SEED_KEYWORDS
    if settings.TARGET_KEYWORDS.strip():
        keywords_to_use = [k.strip() for k in settings.TARGET_KEYWORDS.split(',') if k.strip()]

    for keyword in keywords_to_use:
        try:
            pytrends.build_payload([keyword], timeframe='today 3-m')
            related = pytrends.related_queries()
            rising = related.get(keyword, {}).get('rising')

            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    query = row['query']
                    value = row['value']  # 'Breakout' or numeric rise %
                    posts.append({
                        "id": f"trends_{hash(query)}",
                        "source": "trends",
                        "content": f"Rising search query: {query} (from seed: {keyword})",
                        "metadata": {"keyword": query, "rise": value, "seed": keyword}
                    })
            time.sleep(2)  # Respect rate limits
        except Exception as e:
            print(f"Trends error for '{keyword}': {e}")

    print(f"Google Trends: collected {len(posts)} rising queries")
    return posts
