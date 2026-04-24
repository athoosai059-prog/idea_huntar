import logging
import random
from backend.db.database import get_all_ideas, save_demand_metrics

log = logging.getLogger(__name__)

def run_demand_scan():
    """
    Mock Demand Scanner.
    In a real scenario, this would use DataForSEO, Ahrefs, or Semrush APIs
    to get real search volume and keyword difficulty for the idea's keywords.
    """
    log.info("Starting Demand Scanner...")
    # Fetch top ideas (e.g., score >= 7) to scan
    ideas = get_all_ideas(min_score=7.0)
    
    scanned_count = 0
    for idea in ideas:
        # Mocking data based on a hash of the idea name so it stays consistent
        seed = sum(ord(c) for c in idea['name'])
        random.seed(seed)
        
        # Fake metrics
        search_volume = random.randint(100, 50000)
        keyword_difficulty = random.randint(10, 85)
        cpc = round(random.uniform(0.5, 15.0), 2)
        
        save_demand_metrics(idea['id'], search_volume, keyword_difficulty, cpc)
        scanned_count += 1

    log.info(f"Demand Scanner finished. Scanned {scanned_count} ideas.")
    return scanned_count
