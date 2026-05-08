from pytrends.request import TrendReq
import time
from backend.config import settings
from backend.utils.logging_config import get_logger
from backend.utils.retry_logic import retry_with_backoff, GOOGLE_TRENDS_RATE_LIMITER

log = get_logger(__name__)

SEED_KEYWORDS = [
    "productivity app", "freelancer tool", "SaaS automation",
    "AI assistant", "remote work tool", "budget tracker app"
]

@retry_with_backoff(max_retries=3, base_delay=2.0, retry_exceptions=(Exception,))
def fetch_trends_data(pytrends, keyword):
    """Fetch Google Trends data with retry logic."""
    # Rate limiting
    if not GOOGLE_TRENDS_RATE_LIMITER.acquire():
        wait_time = GOOGLE_TRENDS_RATE_LIMITER.wait_time()
        log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        time.sleep(wait_time)

    log.debug(f"Analyzing keyword: {keyword}")
    pytrends.build_payload([keyword], timeframe='today 3-m')
    related = pytrends.related_queries()
    return related.get(keyword, {}).get('rising')

def run():
    """Scrape Google Trends for rising search queries."""
    log.info("Starting Google Trends scraper...")

    try:
        pytrends = TrendReq(hl='en-US', tz=360)
    except Exception as e:
        log.error(f"Failed to initialize pytrends: {e}")
        return []

    posts = []

    # Use user-defined target keywords if available, otherwise default seeds
    keywords_to_use = SEED_KEYWORDS
    if settings.TARGET_KEYWORDS.strip():
        keywords_to_use = [k.strip() for k in settings.TARGET_KEYWORDS.split(',') if k.strip()]

    log.debug(f"Scanning {len(keywords_to_use)} keywords")

    for keyword in keywords_to_use:
        try:
            rising = fetch_trends_data(pytrends, keyword)

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

            # Additional delay between keywords
            time.sleep(2)

        except Exception as e:
            log.error(f"Trends error for '{keyword}': {e}")
            continue

    log.info(f"Google Trends: collected {len(posts)} rising queries")
    return posts
