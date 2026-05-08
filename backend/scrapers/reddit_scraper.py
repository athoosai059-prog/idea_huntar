import requests
import hashlib
import time
from datetime import datetime
from backend.config import settings
from backend.utils.logging_config import get_logger
from backend.utils.retry_logic import retry_with_backoff, REDDIT_RATE_LIMITER

log = get_logger(__name__)

SUBREDDITS = ["SideProject", "startups", "webdev", "entrepreneur", "freelance",
              "Startup_Ideas", "AppIdeas", "SomebodyMakeThis", "indiehackers"]

COMPLAINT_KEYWORDS = [
    "wish there was", "why isn't there", "I need an app",
    "frustrated with", "nobody has built", "can't find a tool",
    "hate that", "annoying that", "if only there was",
    "looking for", "alternative to", "is there a", "need help",
    "what tool", "any recommendations", "struggling with"
]

# Rotate sort types to get different posts each run
SORT_TYPES = ["new", "hot", "rising"]

@retry_with_backoff(max_retries=3, base_delay=2.0, retry_exceptions=(Exception,))
def scrape_subreddit(sub_name, sort_type="new"):
    """Scrape a single subreddit with retry logic using public JSON API."""
    log.debug(f"Scraping r/{sub_name}/{sort_type}")
    posts = []

    url = f"https://www.reddit.com/r/{sub_name}/{sort_type}.json?limit=50"
    headers = {"User-Agent": settings.REDDIT_USER_AGENT or "IdeaHunter:v1.0 (by /u/ideahunter)"}

    # Rate limiting
    if not REDDIT_RATE_LIMITER.acquire():
        wait_time = REDDIT_RATE_LIMITER.wait_time()
        log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        time.sleep(wait_time)

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    for child in data.get("data", {}).get("children", []):
        submission = child.get("data", {})
        score = submission.get("score", 0)
        
        # For 'new' sort, lower the bar to catch fresh posts
        min_score = 3 if sort_type == "new" else 10
        if score < min_score:
            continue

        title = submission.get("title", "")
        selftext = submission.get("selftext", "")
        content = f"{title}\n{selftext[:2000]}"

        permalink = submission.get('permalink', '')
        reddit_url = f"https://reddit.com{permalink}" if permalink else ""

        # Use the Reddit post's unique ID (not hashed) + timestamp for uniqueness
        reddit_id = submission.get("id", "")
        created_utc = submission.get("created_utc", 0)
        unique_id = f"reddit_{reddit_id}_{int(created_utc)}"

        posts.append({
            "id": unique_id,
            "source": "reddit",
            "content": content,
            "url": reddit_url,
            "metadata": {
                "subreddit": sub_name,
                "upvotes": score,
                "url": reddit_url,
                "sort": sort_type,
                "has_signal": any(kw.lower() in content.lower() for kw in COMPLAINT_KEYWORDS)
            }
        })

    return posts

def run():
    """Scrape Reddit for potential app ideas using public JSON."""
    log.info("Starting Reddit scraper...")

    # Pick a sort type based on current hour to rotate automatically
    hour = datetime.now().hour
    sort_type = SORT_TYPES[hour % len(SORT_TYPES)]
    log.info(f"Reddit: using '{sort_type}' sort this run")

    posts = []
    for sub_name in SUBREDDITS:
        try:
            sub_posts = scrape_subreddit(sub_name, sort_type)
            posts.extend(sub_posts)
            time.sleep(2)  # be nice to Reddit
        except Exception as e:
            log.error(f"Reddit scraper error for {sub_name}: {e}")
            continue

    log.info(f"Reddit: collected {len(posts)} posts")
    return posts
