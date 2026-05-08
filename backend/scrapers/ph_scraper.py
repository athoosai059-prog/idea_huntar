import requests
import time
from backend.config import settings
from backend.utils.logging_config import get_logger
from backend.utils.retry_logic import retry_with_backoff, PRODUCTHUNT_RATE_LIMITER

log = get_logger(__name__)

@retry_with_backoff(max_retries=3, base_delay=2.0, retry_exceptions=(requests.exceptions.RequestException,))
def fetch_producthunt_data(headers, query):
    """Fetch Product Hunt data with retry logic."""
    url = "https://api.producthunt.com/v2/api/graphql"

    # Rate limiting
    if not PRODUCTHUNT_RATE_LIMITER.acquire():
        wait_time = PRODUCTHUNT_RATE_LIMITER.wait_time()
        log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        time.sleep(wait_time)

    log.debug(f"Requesting Product Hunt API: {url}")
    response = requests.post(url, json={'query': query}, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def run():
    """Scrape Product Hunt for potential app ideas."""
    if not settings.PRODUCTHUNT_TOKEN:
        log.warning("Product Hunt scraper: Missing token, skipping.")
        return []

    log.info("Starting Product Hunt scraper...")

    headers = {"Authorization": f"Bearer {settings.PRODUCTHUNT_TOKEN}"}

    # Query for newest posts or specific categories
    query = """
    {
      posts(first: 50, order: NEWEST) {
        edges {
          node {
            id
            name
            tagline
            description
            votesCount
            website
          }
        }
      }
    }
    """

    posts = []
    try:
        data = fetch_producthunt_data(headers, query)

        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            content = f"{node.get('name')}: {node.get('tagline')}\n{node.get('description') or ''}"
            posts.append({
                "id": f"ph_{node.get('id')}",
                "source": "producthunt",
                "content": content,
                "metadata": {
                    "votes": node.get("votesCount", 0),
                    "url": node.get("website")
                }
            })
        log.info(f"Product Hunt: collected {len(posts)} posts")

    except Exception as e:
        log.error(f"Product Hunt scraper error: {e}")

    return posts
