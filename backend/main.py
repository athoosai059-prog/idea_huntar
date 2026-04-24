import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from backend.scrapers import reddit_scraper, playstore_scraper, trends_scraper, hn_scraper, ph_scraper, ih_scraper, twitter_scraper
from backend.ai.analyzer import run_analysis
from backend.validators.validator import validate_ideas
from backend.db.database import init_db, save_raw_posts, get_unprocessed_posts, save_ideas, mark_posts_processed, log_run
from backend.pipelines.demand_scanner import run_demand_scan
from backend.pipelines.gsc_monitor import run_gsc_monitor
from backend.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def run_pipeline():
    log.info("=== Pipeline started ===")
    
    # Step 1: Collect raw data from all sources
    all_posts = []
    scrapers = [
        (reddit_scraper, "reddit"),
        (playstore_scraper, "playstore"),
        (trends_scraper, "trends"),
        (hn_scraper, "hn"),
        (ph_scraper, "ph"),
        (ih_scraper, "ih"),
        (twitter_scraper, "twitter")
    ]
    
    for scraper_module, name in scrapers:
        try:
            log.info(f"Running {name} scraper...")
            posts = scraper_module.run()
            all_posts.extend(posts)
            log_run(name, len(posts), status="ok")
        except Exception as e:
            log.error(f"Scraper {name} failed: {e}")
            log_run(name, 0, status="error", error=str(e))

    log.info(f"Total raw posts collected: {len(all_posts)}")
    
    # Filter by TARGET_KEYWORDS if set
    if settings.TARGET_KEYWORDS.strip():
        keywords = [k.strip().lower() for k in settings.TARGET_KEYWORDS.split(',') if k.strip()]
        filtered_posts = []
        for post in all_posts:
            content_lower = post.get('content', '').lower()
            if any(kw in content_lower for kw in keywords):
                filtered_posts.append(post)
        log.info(f"Filtered by keywords '{settings.TARGET_KEYWORDS}': {len(filtered_posts)} remaining")
        all_posts = filtered_posts

    if all_posts:
        save_raw_posts(all_posts)

    # Step 2: Get unprocessed posts for AI analysis
    unprocessed = get_unprocessed_posts(limit=500)
    if not unprocessed:
        log.info("No new posts to analyze.")
        return

    # Step 3: AI analysis
    try:
        ideas = run_analysis(unprocessed)
        
        # Step 4: Validation
        ideas = validate_ideas(ideas)

        # Step 5: Save only ideas above threshold
        good_ideas = [i for i in ideas if i.get("score_overall", 0) >= settings.MIN_IDEA_SCORE]
        if good_ideas:
            save_ideas(good_ideas)
            
        # Mark processed
        mark_posts_processed([p["id"] for p in unprocessed])
        
        log.info(f"Pipeline complete. {len(good_ideas)} ideas saved (score >= {settings.MIN_IDEA_SCORE})")
        log_run("pipeline_ai", len(unprocessed), len(good_ideas), status="ok")
        
        # Run additional pipelines
        log.info("Running Demand Scanner and GSC Monitor...")
        run_demand_scan()
        run_gsc_monitor()
        
    except Exception as e:
        log.error(f"Pipeline processing failed: {e}")
        log_run("pipeline_ai", len(unprocessed), 0, status="error", error=str(e))

def start():
    init_db()
    scheduler = BlockingScheduler()
    # Parse cron from settings (e.g. "0 6 * * *")
    parts = settings.SCRAPE_SCHEDULE.split()
    scheduler.add_job(run_pipeline, 'cron',
        minute=parts[0], hour=parts[1], day=parts[2],
        month=parts[3], day_of_week=parts[4])

    log.info(f"Scheduler started. Next run: {scheduler.get_jobs()[0].next_run_time}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        init_db()
        run_pipeline()   # Manual one-time run
    else:
        start()          # Scheduled daemon
