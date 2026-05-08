import random
from backend.db.database import get_saved_ideas, save_gsc_metrics
from backend.utils.logging_config import get_logger

log = get_logger(__name__)

def run_gsc_monitor():
    """
    Mock Post-Launch Monitor (Google Search Console).
    In a real scenario, this would authenticate with Google APIs
    and fetch impressions, clicks, CTR, and position.
    """
    log.info("Starting GSC Post-Launch Monitor...")

    # Only track ideas that are marked as "saved" (our proxy for launched/tracked)
    saved_ideas = get_saved_ideas()

    if not saved_ideas:
        log.info("No saved ideas to monitor")
        return 0

    log.info(f"Monitoring {len(saved_ideas)} saved ideas...")

    tracked_count = 0
    for idea in saved_ideas:
        try:
            # Generate some mock progression based on ID to make it look realistic
            base_impressions = 1000 + (idea['id'] * 150)
            base_clicks = int(base_impressions * random.uniform(0.01, 0.08))
            position = round(random.uniform(5.0, 50.0), 1)
            ctr = round((base_clicks / base_impressions) * 100, 2) if base_impressions > 0 else 0

            save_gsc_metrics(idea['id'], base_impressions, base_clicks, position, ctr)
            tracked_count += 1

            log.debug(f"Updated GSC metrics for idea {idea['id']}: {base_impressions} impressions, {base_clicks} clicks, position {position}")

        except Exception as e:
            log.error(f"Error monitoring idea {idea['id']}: {e}")
            continue

    log.info(f"GSC Monitor finished. Tracked {tracked_count} saved ideas.")
    return tracked_count
