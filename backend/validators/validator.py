import requests
from backend.config import settings

def check_search_volume(keyword: str) -> int:
    """Returns 0-100 demand score. Uses SerpAPI if key available, else estimates."""
    if not settings.SERPAPI_KEY:
        # Default mid-score without API
        return 50 

    try:
        r = requests.get("https://serpapi.com/search", params={
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "q": keyword,
            "num": 10
        }, timeout=10)
        data = r.json()
        results_count = int(data.get("search_information", {}).get("total_results", 0))
        # Normalize to 0-100
        if results_count > 10_000_000: return 90
        if results_count > 1_000_000: return 70
        if results_count > 100_000: return 50
        if results_count > 10_000: return 30
        return 10
    except Exception:
        return 50

def check_competition(keyword: str) -> int:
    """Returns 0-100 competition score (lower = better opportunity)."""
    if not settings.SERPAPI_KEY:
        return 40

    try:
        r = requests.get("https://serpapi.com/search", params={
            "api_key": settings.SERPAPI_KEY,
            "engine": "google_play",
            "q": keyword
        }, timeout=10)

        if r.status_code == 200:
            apps = r.json().get("organic_results", [])
            # 0-5 results = low competition
            if len(apps) < 3: return 15
            if len(apps) < 6: return 35
            if len(apps) < 10: return 60
            return 80
        return 40
    except Exception:
        return 40

def validate_ideas(ideas: list[dict]) -> list[dict]:
    """Enhance each idea's scores with validation data."""
    validated = []
    for idea in ideas:
        if not idea.get("keywords"):
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

    return validated
