import requests
import hashlib
import time
from backend.utils.logging_config import get_logger

log = get_logger(__name__)

# IndieHackers.com no longer has a public RSS feed.
# Strategy: Scrape the IndieHackers-related subreddits + use Google cache snippets
# to surface IH-style content (bootstrapped SaaS, solo founders, side projects).

IH_SUBREDDITS = ["indiehackers", "EntrepreneurRideAlong", "microSaaS"]

SIGNAL_KEYWORDS = [
    "problem", "stuck", "frustrated", "annoying", "wish", "how to",
    "need help", "idea", "looking for", "can't find", "nobody builds",
    "pain", "struggle", "alternative to", "better way", "building",
    "launched", "revenue", "mrr", "churn", "validate"
]

def run():
    """Scrapes IndieHackers-style content from related subreddits."""
    log.info("Starting IndieHackers scraper (via subreddit proxies)...")

    results = []
    
    for sub in IH_SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=50"
            headers = {"User-Agent": "IdeaHunter:v1.0 (by /u/ideahunter)"}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "").strip()
                selftext = post.get("selftext", "").strip()
                content = f"{title}\n{selftext[:2000]}"
                
                content_lower = content.lower()
                if not any(kw in content_lower for kw in SIGNAL_KEYWORDS):
                    continue
                
                reddit_id = post.get("id", "")
                created = post.get("created_utc", 0)
                permalink = post.get("permalink", "")
                reddit_url = f"https://reddit.com{permalink}" if permalink else ""
                
                post_id = hashlib.md5(f"{reddit_id}_{int(created)}".encode()).hexdigest()
                
                results.append({
                    "id": f"ih_{post_id}",
                    "source": "ih",
                    "content": content,
                    "url": reddit_url,
                    "metadata": {
                        "url": reddit_url,
                        "title": title,
                        "subreddit": sub,
                        "upvotes": post.get("score", 0)
                    }
                })
            
            log.debug(f"IH proxy r/{sub}: {len(results)} posts so far")
            time.sleep(2)
            
        except Exception as e:
            log.error(f"IndieHackers proxy scraper failed for r/{sub}: {e}")

    log.info(f"IndieHackers: collected {len(results)} posts")
    return results
