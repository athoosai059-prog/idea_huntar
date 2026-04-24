import requests
from bs4 import BeautifulSoup
import logging

log = logging.getLogger(__name__)

def run():
    """Scrapes the 'Questions' and 'Ideas' groups on IndieHackers."""
    results = []
    # IndieHackers groups/threads
    urls = [
        "https://www.indiehackers.com/group/questions",
        "https://www.indiehackers.com/group/ideas"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for url in urls:
        try:
            log.info(f"IndieHackers: Scraping {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # NEW: IndieHackers uses .story for each post container
            posts = soup.find_all('div', class_='story')
            
            for post in posts:
                title_link = post.find('a', class_='story__text-link')
                if not title_link:
                    continue
                    
                title_elem = title_link.find('h3')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text().strip()
                link = "https://www.indiehackers.com" + title_link['href']
                
                # Filter for interesting keywords
                if any(k in title.lower() for k in ["problem", "stuck", "frustrated", "annoying", "wish", "how to", "need help", "idea"]):
                    results.append({
                        "source": "ih",
                        "source_id": link,
                        "content": title,
                        "url": link
                    })
            log.info(f"IndieHackers: Found {len(results)} matches on {url}")
        except Exception as e:
            log.error(f"IndieHackers scraper failed for {url}: {e}")
            
    return results
