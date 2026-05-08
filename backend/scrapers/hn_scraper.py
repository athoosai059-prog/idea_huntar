import requests
import time
import math
from datetime import datetime, timedelta
from backend.utils.logging_config import get_logger
from backend.utils.retry_logic import retry_with_backoff, HACKERNEWS_RATE_LIMITER

log = get_logger(__name__)

# Multiple query patterns to surface different kinds of opportunities
SEARCH_QUERIES = [
    {"query": "need app", "tags": "ask_hn", "label": "app requests"},
    {"query": "wish there was", "tags": "ask_hn,comment", "label": "wishlists"},
    {"query": "frustrated with", "tags": "comment", "label": "frustrations"},
    {"query": "alternative to", "tags": "story", "label": "alternatives"},
    {"query": "Show HN", "tags": "show_hn", "label": "launches"},
]

@retry_with_backoff(max_retries=3, base_delay=1.0, retry_exceptions=(requests.exceptions.RequestException,))
def fetch_hackernews_data(params):
    """Fetch HackerNews data with retry logic."""
    url = "https://hn.algolia.com/api/v1/search_by_date"  # search_by_date = freshest results

    # Rate limiting
    if not HACKERNEWS_RATE_LIMITER.acquire():
        wait_time = HACKERNEWS_RATE_LIMITER.wait_time()
        log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        time.sleep(wait_time)

    log.debug(f"Requesting HN API: {url} with params: {params}")
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def run():
    """Scrape HackerNews for potential app ideas — time-filtered for freshness."""
    log.info("Starting HackerNews scraper...")

    # Only fetch posts from the last 7 days to ensure freshness
    week_ago = datetime.utcnow() - timedelta(days=7)
    timestamp = int(week_ago.timestamp())

    posts = []
    seen_ids = set()

    for search_config in SEARCH_QUERIES:
        try:
            params = {
                "query": search_config["query"],
                "tags": search_config["tags"],
                "numericFilters": f"created_at_i>{timestamp},points>5",
                "hitsPerPage": 50
            }

            data = fetch_hackernews_data(params)
            hits = data.get("hits", []) if isinstance(data, dict) else []

            for hit in hits:
                obj_id = hit['objectID']
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                hn_url = f"https://news.ycombinator.com/item?id={obj_id}"
                title = hit.get('title', '') or ''
                story_text = hit.get('story_text', '') or ''
                comment_text = hit.get('comment_text', '') or ''
                
                content = f"{title}\n{story_text or comment_text}"[:3000]
                if len(content.strip()) < 20:
                    continue

                posts.append({
                    "id": f"hn_{obj_id}",
                    "source": "hn",
                    "content": content,
                    "url": hn_url,
                    "metadata": {
                        "points": hit.get("points", 0),
                        "url": hn_url,
                        "external_url": hit.get("url", ""),
                        "query": search_config["label"],
                        "created_at": hit.get("created_at", "")
                    }
                })

            log.info(f"HN [{search_config['label']}]: {len(hits)} hits")
            time.sleep(1)  # Be polite between queries

        except Exception as e:
            log.error(f"HN scraper error for '{search_config['label']}': {e}")

    log.info(f"HackerNews: collected {len(posts)} posts")
    return posts
