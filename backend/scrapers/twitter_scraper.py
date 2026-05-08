import requests
import hashlib
import time
import re
from backend.utils.logging_config import get_logger

log = get_logger(__name__)

# Since all Nitter instances are dead and Twitter API costs $100/mo,
# we use DuckDuckGo HTML search to find recent tweets containing pain-point keywords.
# This surfaces real Twitter/X posts without any API key.

SEARCH_QUERIES = [
    'site:twitter.com "i wish there was an app"',
    'site:twitter.com "why is there no tool"',
    'site:twitter.com "can someone build"',
    'site:twitter.com "frustrated with" software',
    'site:twitter.com "is there an alternative to"',
    'site:x.com "i need a tool that"',
    'site:x.com "someone should build"',
    'site:x.com "looking for an app"',
]

SIGNAL_KEYWORDS = [
    "wish", "frustrated", "terrible", "broken", "why isn't",
    "can someone", "nobody built", "need a tool", "looking for",
    "alternative", "annoying", "hate", "awful"
]

def _search_ddg(query):
    """Search DuckDuckGo HTML for tweets matching a query."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.post(url, data={"q": query}, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        results = []
        # Parse snippets from DDG HTML results
        # Each result has a class "result__snippet" and "result__url"
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        url_pattern = re.compile(
            r'<a[^>]*class="result__url"[^>]*href="([^"]*)"[^>]*>',
            re.DOTALL
        )
        title_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        
        snippets = snippet_pattern.findall(html)
        urls = url_pattern.findall(html)
        titles = title_pattern.findall(html)
        
        for i in range(min(len(snippets), len(urls))):
            # Clean HTML tags from snippet
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
            result_url = urls[i].strip()
            
            # Only keep twitter/x.com results
            if 'twitter.com' not in result_url and 'x.com' not in result_url:
                continue
                
            results.append({
                "title": title,
                "snippet": snippet,
                "url": result_url
            })
        
        return results
        
    except Exception as e:
        log.warning(f"DDG search failed for '{query}': {e}")
        return []

def run():
    """Scrapes Twitter/X pain-point posts via DuckDuckGo search — no API key needed."""
    log.info("Starting Twitter scraper (via DuckDuckGo search)...")

    results = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        try:
            log.debug(f"Twitter/DDG: searching '{query}'")
            search_results = _search_ddg(query)
            
            for sr in search_results:
                url = sr["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                content = f"{sr['title']}\n{sr['snippet']}"
                content_lower = content.lower()
                
                # Check for pain-point signals
                if not any(kw in content_lower for kw in SIGNAL_KEYWORDS):
                    continue
                
                post_id = hashlib.md5(url.encode()).hexdigest()
                
                # Normalize URL to twitter.com format
                twitter_url = url.replace("x.com", "twitter.com")
                
                results.append({
                    "id": f"twitter_{post_id}",
                    "source": "twitter",
                    "content": content[:2000],
                    "url": twitter_url,
                    "metadata": {
                        "url": twitter_url,
                        "query": query
                    }
                })
            
            log.debug(f"Twitter/DDG: '{query}' -> {len(search_results)} raw, {len(results)} signal posts total")
            
        except Exception as e:
            log.warning(f"Twitter search failed for '{query}': {e}")
        
        time.sleep(3)  # Be polite between searches

    log.info(f"Twitter: collected {len(results)} tweets")
    return results
