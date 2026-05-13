"""
Demand Scanner Pipeline — uses SerpAPI for real search intelligence.
Falls back to AI-estimated scores if SerpAPI key is missing.
"""
import json
import requests
import time
from backend.db.database import get_all_ideas, save_demand_metrics
from backend.config import settings
from backend.utils.logging_config import get_logger

log = get_logger(__name__)


def _get_serp_data(keyword: str) -> dict | None:
    """Query SerpAPI for real search results data."""
    if not settings.SERPAPI_KEY:
        return None
    try:
        response = requests.get("https://serpapi.com/search", params={
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "q": keyword,
            "num": 10,
        }, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.warning(f"SerpAPI request failed for '{keyword}': {e}")
        return None


def _estimate_search_volume(serp_data: dict) -> int:
    """Estimate search volume from SERP data (total results count)."""
    if not serp_data:
        return 1000  # default

    total_results = int(serp_data.get("search_information", {}).get("total_results", 0))

    # Map total results to estimated monthly search volume
    if total_results > 1_000_000_000:
        return 50000
    elif total_results > 100_000_000:
        return 30000
    elif total_results > 10_000_000:
        return 15000
    elif total_results > 1_000_000:
        return 5000
    elif total_results > 100_000:
        return 1500
    elif total_results > 10_000:
        return 500
    else:
        return 100


def _estimate_keyword_difficulty(serp_data: dict) -> int:
    """Estimate keyword difficulty from SERP features and top results."""
    if not serp_data:
        return 50  # default medium

    difficulty = 30  # base

    # Ads present = high commercial value = harder to rank
    ads = serp_data.get("ads", [])
    if len(ads) >= 4:
        difficulty += 25
    elif len(ads) >= 2:
        difficulty += 15
    elif len(ads) >= 1:
        difficulty += 8

    # Featured snippet = Google considers query well-answered = harder
    if serp_data.get("answer_box") or serp_data.get("featured_snippet"):
        difficulty += 10

    # Knowledge panel = entity query = very competitive
    if serp_data.get("knowledge_graph"):
        difficulty += 10

    # Check if top results are from big authority domains
    organic = serp_data.get("organic_results", [])
    big_domains = {"wikipedia.org", "amazon.com", "youtube.com", "facebook.com",
                   "twitter.com", "linkedin.com", "reddit.com", "github.com",
                   "medium.com", "forbes.com", "techcrunch.com"}
    authority_count = 0
    for r in organic[:5]:
        link = r.get("link", "")
        for domain in big_domains:
            if domain in link:
                authority_count += 1
                break

    difficulty += authority_count * 5

    return min(95, max(5, difficulty))


def _estimate_cpc(serp_data: dict) -> float:
    """Estimate CPC from ad presence in SERP."""
    if not serp_data:
        return 1.50  # default

    ads = serp_data.get("ads", [])
    if len(ads) >= 4:
        return 8.50  # highly commercial
    elif len(ads) >= 2:
        return 4.25
    elif len(ads) >= 1:
        return 2.00
    else:
        return 0.50  # low commercial intent


def run_demand_scan():
    """
    Real Demand Scanner using SerpAPI.
    For each top idea's primary keyword, queries Google and analyzes SERP features.
    Falls back to reasonable estimates if SerpAPI key is missing.
    """
    log.info("Starting Demand Scanner...")

    ideas = get_all_ideas(min_score=5.0)

    if not ideas:
        log.info("No ideas found with score >= 5.0")
        return 0

    log.info(f"Scanning {len(ideas)} ideas for demand metrics...")

    has_serpapi = bool(settings.SERPAPI_KEY)
    if not has_serpapi:
        log.warning("No SERPAPI_KEY configured — using AI-estimated demand scores")

    scanned_count = 0
    for idea in ideas:
        try:
            # Get primary keyword
            keywords = idea.get('keywords', [])
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except Exception:
                    keywords = []

            if not keywords:
                log.debug(f"Idea {idea['id']}: No keywords, skipping")
                continue

            primary_keyword = keywords[0]

            if has_serpapi:
                # Real SerpAPI data
                serp_data = _get_serp_data(primary_keyword)
                search_volume = _estimate_search_volume(serp_data)
                keyword_difficulty = _estimate_keyword_difficulty(serp_data)
                cpc = _estimate_cpc(serp_data)

                # Rate limit: SerpAPI free tier = 100 searches/month
                time.sleep(2)
            else:
                # Estimate based on keyword characteristics
                word_count = len(primary_keyword.split())
                if word_count <= 1:
                    search_volume = 10000
                    keyword_difficulty = 75
                    cpc = 5.00
                elif word_count <= 3:
                    search_volume = 3000
                    keyword_difficulty = 50
                    cpc = 2.50
                else:
                    search_volume = 800
                    keyword_difficulty = 30
                    cpc = 1.25

            save_demand_metrics(idea['id'], search_volume, keyword_difficulty, cpc)
            scanned_count += 1
            log.debug(f"Scanned idea {idea['id']}: {idea['name']} — Vol: {search_volume}, KD: {keyword_difficulty}, CPC: ${cpc}")

        except Exception as e:
            log.error(f"Error scanning idea {idea['id']}: {e}")
            continue

    log.info(f"Demand Scanner finished. Scanned {scanned_count} ideas.")
    return scanned_count
