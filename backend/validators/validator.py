import requests
import time
from backend.config import settings
from backend.utils.logging_config import get_logger
from backend.utils.retry_logic import retry_with_backoff, SERPAPI_RATE_LIMITER
from backend.utils.cache import cached, generate_validation_cache_key, get_cached_result, cache_result

log = get_logger(__name__)

@retry_with_backoff(max_retries=3, base_delay=1.0, retry_exceptions=(requests.exceptions.RequestException,))
def fetch_serpapi_data(engine, params):
    """Fetch SerpAPI data with retry logic."""
    # Rate limiting
    if not SERPAPI_RATE_LIMITER.acquire():
        wait_time = SERPAPI_RATE_LIMITER.wait_time()
        log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        time.sleep(wait_time)

    log.debug(f"Requesting SerpAPI: engine={engine}, params={params}")
    response = requests.get("https://serpapi.com/search", params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def check_search_volume(keyword: str) -> int:
    """Returns 0-100 demand score. Uses SerpAPI if key available, else estimates."""
    if not settings.SERPAPI_KEY:
        log.debug(f"No SerpAPI key, using default score for keyword: {keyword}")
        return 50

    # Check cache first
    cache_key = generate_validation_cache_key(f"search_volume:{keyword}")
    cached_result = get_cached_result(cache_key)
    if cached_result is not None:
        log.debug(f"Cache hit for search volume: {keyword}")
        return cached_result

    try:
        data = fetch_serpapi_data("google", {
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "q": keyword,
            "num": 10
        })

        results_count = int(data.get("search_information", {}).get("total_results", 0))

        # Normalize to 0-100
        if results_count > 10_000_000:
            score = 90
        elif results_count > 1_000_000:
            score = 70
        elif results_count > 100_000:
            score = 50
        elif results_count > 10_000:
            score = 30
        else:
            score = 10

        log.debug(f"Search volume for '{keyword}': {results_count} results -> score: {score}")

        # Cache result for 24 hours
        cache_result(cache_key, score, ttl=86400)
        return score

    except Exception as e:
        log.error(f"Error checking search volume for '{keyword}': {e}")
        return 50

def check_competition(keyword: str) -> int:
    """Returns 0-100 competition score (lower = better opportunity)."""
    if not settings.SERPAPI_KEY:
        log.debug(f"No SerpAPI key, using default competition score for keyword: {keyword}")
        return 40

    # Check cache first
    cache_key = generate_validation_cache_key(f"competition:{keyword}")
    cached_result = get_cached_result(cache_key)
    if cached_result is not None:
        log.debug(f"Cache hit for competition: {keyword}")
        return cached_result

    try:
        data = fetch_serpapi_data("google_play", {
            "api_key": settings.SERPAPI_KEY,
            "engine": "google_play",
            "q": keyword
        })

        apps = data.get("organic_results", [])
        # 0-5 results = low competition
        if len(apps) < 3:
            score = 15
        elif len(apps) < 6:
            score = 35
        elif len(apps) < 10:
            score = 60
        else:
            score = 80

        log.debug(f"Competition for '{keyword}': {len(apps)} apps -> score: {score}")

        # Cache result for 24 hours
        cache_result(cache_key, score, ttl=86400)
        return score

    except Exception as e:
        log.error(f"Error checking competition for '{keyword}': {e}")
        return 40

def validate_ideas(ideas: list[dict]) -> list[dict]:
    """Enhance each idea's scores with validation data."""
    log.info(f"Validating {len(ideas)} ideas...")

    validated = []
    for idx, idea in enumerate(ideas):
        try:
            if not idea.get("keywords"):
                log.debug(f"Idea {idx + 1}: No keywords, skipping validation")
                validated.append(idea)
                continue

            primary_keyword = idea["keywords"][0]
            demand_check = check_search_volume(primary_keyword)
            competition_check = check_competition(primary_keyword)

            # Blend AI score with validation data
            idea["score_demand"] = round((idea.get("score_demand", 50) + demand_check) / 2)
            idea["score_competition"] = round((idea.get("score_competition", 50) + competition_check) / 2)

            # Recalculate overall
            d = idea["score_demand"]
            c = 100 - idea["score_competition"]
            t = idea.get("score_trend", 50)
            u = idea.get("score_uniqueness", 50)
            idea["score_overall"] = round((d * 0.35 + c * 0.25 + t * 0.25 + u * 0.15) / 10, 1)

            validated.append(idea)

        except Exception as e:
            log.error(f"Error validating idea {idx + 1}: {e}")
            validated.append(idea)  # Keep original idea if validation fails

    log.info(f"Validation complete. {len(validated)} ideas processed.")
    return validated
