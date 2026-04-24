import requests
from bs4 import BeautifulSoup
import logging
import random
import time

log = logging.getLogger(__name__)

# List of public Nitter instances (mirrors of Twitter)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.it",
    "https://nitter.privacydev.net",
    "https://nitter.moomoo.me",
    "https://nitter.unixfox.eu"
]

def run():
    """Scrapes Twitter/X using Nitter search feeds for pain points."""
    results = []
    queries = [
        '"i wish there was an app for"',
        '"is there a tool for"',
        '"why is there no app that"',
        '"this software is so bad"',
        '"can someone build a"'
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    for query in queries:
        # Try up to 3 random instances for each query
        instances_to_try = random.sample(NITTER_INSTANCES, 3)
        success = False
        
        for instance in instances_to_try:
            try:
                # Search URL format for Nitter
                search_url = f"{instance}/search?f=tweets&q={query}"
                log.info(f"Twitter (Nitter): Searching {query} on {instance}...")
                
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    log.warning(f"Nitter instance {instance} returned {response.status_code}")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                # Nitter's main tweet container
                tweets = soup.find_all('div', class_='timeline-item')
                
                if not tweets:
                    log.warning(f"No tweets found on {instance} for {query}")
                    continue
                
                query_found = 0
                for tweet in tweets:
                    content_elem = tweet.find('div', class_='tweet-content')
                    if not content_elem:
                        continue
                        
                    content = content_elem.get_text().strip()
                    tweet_link_elem = tweet.find('a', class_='tweet-link')
                    tweet_id = tweet_link_elem['href'] if tweet_link_elem else content[:20]
                    
                    results.append({
                        "source": "twitter",
                        "source_id": tweet_id,
                        "content": content,
                        "url": instance + tweet_id if tweet_link_elem else ""
                    })
                    query_found += 1
                
                log.info(f"Twitter: Found {query_found} tweets on {instance}")
                success = True
                break # Move to next query
                
            except Exception as e:
                log.error(f"Twitter scraper failed for {query} on {instance}: {e}")
                continue
        
        if not success:
            log.error(f"Failed to scrape Twitter for {query} after trying 3 instances.")
        
        # Small delay to avoid aggressive rate limiting
        time.sleep(1)
            
    return results
