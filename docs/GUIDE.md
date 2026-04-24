# IdeaHunter — Complete Design & Development Guide

## What This App Does

IdeaHunter is your automated research assistant for web app ideas. It runs every day, scrapes 5 data sources, sends the data to Claude AI for analysis, validates each idea with keyword/competition checks, then surfaces a ranked list of opportunities for you to review — all through a clean management dashboard.

---

## Project Structure

```
ideahunter/
├── backend/
│   ├── main.py                  # Pipeline entry point + APScheduler
│   ├── config.py                # All settings loaded from .env
│   ├── scrapers/
│   │   ├── reddit_scraper.py    # PRAW-based Reddit collector
│   │   ├── playstore_scraper.py # google-play-scraper collector
│   │   ├── trends_scraper.py    # pytrends / SerpAPI collector
│   │   ├── hn_scraper.py        # HackerNews Algolia API
│   │   └── ph_scraper.py        # Product Hunt GraphQL API
│   ├── ai/
│   │   └── analyzer.py          # Claude API idea extractor + scorer
│   ├── validators/
│   │   └── validator.py         # Keyword demand + competition checker
│   ├── db/
│   │   ├── database.py          # SQLite setup + queries
│   │   └── schema.sql           # Table definitions
│   └── api/
│       └── routes.py            # Flask REST API for the dashboard
├── frontend/
│   └── dashboard.html           # Full management UI (single file)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Best library support for all scrapers |
| Scheduler | APScheduler | Simple cron-style scheduling in-process |
| Reddit | PRAW | Official Reddit API wrapper |
| Play Store | google-play-scraper | No API key needed, zero dependencies |
| Google Trends | pytrends | Free, no key needed for basic use |
| HackerNews | Algolia API | 100% free, no auth required |
| Product Hunt | GraphQL API | Free with developer account |
| AI Engine | Claude API (Anthropic) | Idea extraction + scoring |
| Validation | SerpAPI (optional) | Keyword volume checking |
| Database | SQLite | Zero setup, perfect for local use |
| Backend API | Flask | Lightweight API for the dashboard |
| Dashboard | Vanilla HTML/CSS/JS | Single file, no build step, instant load |

---

## Phase 1 — Environment Setup

### 1. Create project and install dependencies

```bash
mkdir ideahunter && cd ideahunter
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install praw google-play-scraper pytrends apscheduler flask anthropic requests python-dotenv
```

### 2. Create your .env file

```bash
cp .env.example .env
```

Fill in `.env`:
```
# Claude AI
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-6

# Reddit (get from reddit.com/prefs/apps → create app → script)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=IdeaHunter:v1.0 (by u/yourusername)

# Product Hunt (get from producthunt.com/v2/oauth/applications)
PRODUCTHUNT_TOKEN=your_ph_token

# SerpAPI (optional, free tier = 100 searches/month)
SERPAPI_KEY=your_serpapi_key

# Pipeline settings
SCRAPE_SCHEDULE=0 6 * * *
MIN_IDEA_SCORE=6.0
BATCH_SIZE=100
```

---

## Phase 2 — Database

### db/schema.sql

```sql
CREATE TABLE IF NOT EXISTS raw_posts (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,          -- 'reddit', 'playstore', 'trends', 'hn', 'ph'
  content TEXT NOT NULL,
  metadata TEXT,                 -- JSON: upvotes, subreddit, app_name, etc.
  collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ideas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  pain_point TEXT,
  source TEXT,
  source_ref TEXT,               -- subreddit name, app id, etc.
  keywords TEXT,                 -- JSON array
  score_overall REAL,
  score_demand INTEGER,
  score_competition INTEGER,
  score_trend INTEGER,
  score_uniqueness INTEGER,
  saved INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  source TEXT,
  records_collected INTEGER,
  ideas_found INTEGER,
  status TEXT,
  error TEXT
);
```

### db/database.py

```python
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "ideahunter.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema = Path(__file__).parent / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema.read_text())
    print("Database initialized.")

def save_raw_posts(posts: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO raw_posts (id, source, content, metadata) VALUES (?,?,?,?)",
            [(p["id"], p["source"], p["content"], json.dumps(p.get("metadata", {}))) for p in posts]
        )

def get_unprocessed_posts(limit=500):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM raw_posts WHERE processed=0 LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

def save_ideas(ideas: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO ideas
               (name, description, pain_point, source, keywords,
                score_overall, score_demand, score_competition, score_trend)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(i["name"], i["description"], i["pain_point"], i["source"],
              json.dumps(i.get("keywords", [])),
              i["score_overall"], i["score_demand"],
              i["score_competition"], i["score_trend"])
             for i in ideas]
        )

def get_all_ideas(min_score=0.0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ideas WHERE score_overall >= ? ORDER BY score_overall DESC",
            (min_score,)
        ).fetchall()
    return [dict(r) for r in rows]
```

---

## Phase 3 — Scrapers

### scrapers/reddit_scraper.py

```python
import praw
import hashlib
from config import settings

SUBREDDITS = ["SideProject", "startups", "webdev", "entrepreneur", "freelance"]
COMPLAINT_KEYWORDS = [
    "wish there was", "why isn't there", "I need an app",
    "frustrated with", "nobody has built", "can't find a tool",
    "hate that", "annoying that", "if only there was"
]

def run():
    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )

    posts = []
    for sub_name in SUBREDDITS:
        sub = reddit.subreddit(sub_name)
        for submission in sub.top(time_filter="month", limit=300):
            # Score filter — skip low-engagement posts
            if submission.score < 10:
                continue

            content = f"{submission.title}\n{submission.selftext[:2000]}"

            # Keyword filter — prioritize complaint/wish posts
            has_signal = any(kw.lower() in content.lower() for kw in COMPLAINT_KEYWORDS)

            post_id = hashlib.md5(submission.id.encode()).hexdigest()
            posts.append({
                "id": f"reddit_{post_id}",
                "source": "reddit",
                "content": content,
                "metadata": {
                    "subreddit": sub_name,
                    "upvotes": submission.score,
                    "url": f"https://reddit.com{submission.permalink}",
                    "has_signal": has_signal
                }
            })

    print(f"Reddit: collected {len(posts)} posts")
    return posts
```

### scrapers/playstore_scraper.py

```python
from google_play_scraper import reviews, Sort

# Apps to mine — competitors in your target niche
TARGET_APPS = [
    "com.notion.id",
    "com.todoist.app",
    "com.asana.app",
    "com.basecamp.bc3android",
]

def run():
    posts = []
    for app_id in TARGET_APPS:
        result, _ = reviews(
            app_id,
            lang='en', country='us',
            sort=Sort.NEWEST,
            count=200,
            filter_score_with=None
        )
        for r in result:
            # Only 1-3 star reviews — these contain the pain points
            if r['score'] > 2:
                continue

            posts.append({
                "id": f"ps_{r['reviewId']}",
                "source": "playstore",
                "content": r['content'],
                "metadata": {
                    "app_id": app_id,
                    "rating": r['score'],
                    "thumbs_up": r.get('thumbsUpCount', 0)
                }
            })

    print(f"Play Store: collected {len(posts)} reviews")
    return posts
```

### scrapers/trends_scraper.py

```python
from pytrends.request import TrendReq
import time

SEED_KEYWORDS = [
    "productivity app", "freelancer tool", "SaaS automation",
    "AI assistant", "remote work tool", "budget tracker app"
]

def run():
    pytrends = TrendReq(hl='en-US', tz=360)
    posts = []

    for keyword in SEED_KEYWORDS:
        try:
            pytrends.build_payload([keyword], timeframe='today 3-m')
            related = pytrends.related_queries()
            rising = related.get(keyword, {}).get('rising')

            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    query = row['query']
                    value = row['value']  # 'Breakout' or numeric rise %
                    posts.append({
                        "id": f"trends_{hash(query)}",
                        "source": "trends",
                        "content": f"Rising search query: {query} (from seed: {keyword})",
                        "metadata": {"keyword": query, "rise": value, "seed": keyword}
                    })
            time.sleep(2)  # Respect rate limits
        except Exception as e:
            print(f"Trends error for '{keyword}': {e}")

    print(f"Google Trends: collected {len(posts)} rising queries")
    return posts
```

### scrapers/hn_scraper.py

```python
import requests

def run():
    # HackerNews Algolia API — completely free, no auth
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": "Ask HN: is there an app that",
        "tags": "ask_hn",
        "numericFilters": "points>50",
        "hitsPerPage": 100
    }

    posts = []
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        for hit in data.get("hits", []):
            posts.append({
                "id": f"hn_{hit['objectID']}",
                "source": "hn",
                "content": f"{hit.get('title', '')}\n{hit.get('story_text', '') or ''}",
                "metadata": {"points": hit.get("points", 0), "url": hit.get("url", "")}
            })
    except Exception as e:
        print(f"HN scraper error: {e}")

    print(f"HackerNews: collected {len(posts)} posts")
    return posts
```

---

## Phase 4 — AI Analysis (Claude API)

### ai/analyzer.py

```python
import anthropic
import json
from config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert app idea analyst. You read complaints, reviews,
and forum posts and extract actionable web app opportunities.

For each batch of posts, return a JSON array of ideas. Each idea must have:
- name: Short, memorable app name (3-6 words)
- description: One sentence describing the app (max 25 words)
- pain_point: The exact frustration users expressed (quote-style, max 20 words)
- keywords: Array of 3 SEO keywords this app would target
- score_demand: 1-100 (how many people seem to want this)
- score_competition: 1-100 (how crowded this space is — lower = less competition)
- score_trend: 1-100 (is interest growing?)
- score_uniqueness: 1-100 (how differentiated from existing tools?)

Return ONLY valid JSON array. No markdown, no explanation."""

def analyze_batch(posts: list[dict]) -> list[dict]:
    """Send a batch of raw posts to Claude and get back structured ideas."""

    post_text = "\n\n---\n\n".join([
        f"[{p['source'].upper()}] {p['content'][:500]}"
        for p in posts
    ])

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Extract web app ideas from these {len(posts)} posts:\n\n{post_text}"
        }]
    )

    try:
        text = message.content[0].text.strip()
        ideas = json.loads(text)
        # Add overall score
        for idea in ideas:
            d = idea.get("score_demand", 50)
            c = 100 - idea.get("score_competition", 50)  # Invert — low competition = good
            t = idea.get("score_trend", 50)
            u = idea.get("score_uniqueness", 50)
            idea["score_overall"] = round((d * 0.35 + c * 0.25 + t * 0.25 + u * 0.15) / 10, 1)
        return ideas
    except Exception as e:
        print(f"JSON parse error from Claude: {e}")
        return []

def run_analysis(posts: list[dict]) -> list[dict]:
    """Chunk posts into batches and analyze all of them."""
    batch_size = settings.BATCH_SIZE
    all_ideas = []

    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]
        print(f"Analyzing batch {i//batch_size + 1}/{-(-len(posts)//batch_size)}...")
        ideas = analyze_batch(batch)
        all_ideas.extend(ideas)

    print(f"Claude analysis: {len(all_ideas)} total ideas extracted")
    return all_ideas
```

---

## Phase 5 — Validation Engine

### validators/validator.py

```python
import requests
from config import settings

def check_search_volume(keyword: str) -> int:
    """Returns 0-100 demand score. Uses SerpAPI if key available, else estimates."""
    if not settings.SERPAPI_KEY:
        # Rough estimation via Google autocomplete suggestions count
        return 50  # Default mid-score without API

    try:
        r = requests.get("https://serpapi.com/search", params={
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "q": keyword,
            "num": 10
        }, timeout=10)
        data = r.json()
        results_count = data.get("search_information", {}).get("total_results", 0)
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
    try:
        r = requests.get("https://serpapi.com/search", params={
            "api_key": settings.SERPAPI_KEY,
            "engine": "google_play",
            "q": keyword
        }, timeout=10) if settings.SERPAPI_KEY else None

        if r and r.status_code == 200:
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
```

---

## Phase 6 — Pipeline Orchestrator

### main.py

```python
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from scrapers import reddit_scraper, playstore_scraper, trends_scraper, hn_scraper, ph_scraper
from ai.analyzer import run_analysis
from validators.validator import validate_ideas
from db.database import init_db, save_raw_posts, get_unprocessed_posts, save_ideas
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def run_pipeline():
    log.info("=== Pipeline started ===")

    # Step 1: Collect raw data from all sources
    all_posts = []
    for scraper in [reddit_scraper, playstore_scraper, trends_scraper, hn_scraper, ph_scraper]:
        try:
            posts = scraper.run()
            all_posts.extend(posts)
        except Exception as e:
            log.error(f"Scraper {scraper.__name__} failed: {e}")

    log.info(f"Total raw posts collected: {len(all_posts)}")
    save_raw_posts(all_posts)

    # Step 2: Get unprocessed posts for AI analysis
    unprocessed = get_unprocessed_posts(limit=500)
    if not unprocessed:
        log.info("No new posts to analyze.")
        return

    # Step 3: AI analysis
    ideas = run_analysis(unprocessed)

    # Step 4: Validation
    ideas = validate_ideas(ideas)

    # Step 5: Save only ideas above threshold
    good_ideas = [i for i in ideas if i.get("score_overall", 0) >= settings.MIN_IDEA_SCORE]
    save_ideas(good_ideas)

    log.info(f"Pipeline complete. {len(good_ideas)} ideas saved (score >= {settings.MIN_IDEA_SCORE})")

def start():
    init_db()
    scheduler = BlockingScheduler()
    # Parse cron from settings (e.g. "0 6 * * *")
    parts = settings.SCRAPE_SCHEDULE.split()
    scheduler.add_job(run_pipeline, 'cron',
        minute=parts[0], hour=parts[1], day=parts[2],
        month=parts[3], day_of_week=parts[4])

    log.info(f"Scheduler started. Next run: {scheduler.get_jobs()[0].next_run_time}")
    scheduler.start()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        run_pipeline()   # Manual one-time run
    else:
        start()          # Scheduled daemon
```

---

## Phase 7 — Flask API for Dashboard

### api/routes.py

```python
from flask import Flask, jsonify, request
from db.database import get_all_ideas, get_conn
import json

app = Flask(__name__, static_folder='../frontend', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('dashboard.html')

@app.route('/api/ideas')
def ideas():
    min_score = float(request.args.get('min_score', 0))
    source = request.args.get('source')
    ideas = get_all_ideas(min_score)
    if source:
        ideas = [i for i in ideas if i['source'] == source]
    for i in ideas:
        if isinstance(i.get('keywords'), str):
            i['keywords'] = json.loads(i['keywords'])
    return jsonify(ideas)

@app.route('/api/ideas/<int:idea_id>/save', methods=['POST'])
def save_idea(idea_id):
    with get_conn() as conn:
        conn.execute("UPDATE ideas SET saved=1 WHERE id=?", (idea_id,))
    return jsonify({"ok": True})

@app.route('/api/stats')
def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM ideas WHERE score_overall >= 8").fetchone()[0]
        saved = conn.execute("SELECT COUNT(*) FROM ideas WHERE saved=1").fetchone()[0]
        last_run = conn.execute("SELECT MAX(run_at) FROM run_log").fetchone()[0]
    return jsonify({"total": total, "high_score": high, "saved": saved, "last_run": last_run})

@app.route('/api/run', methods=['POST'])
def trigger_run():
    from main import run_pipeline
    import threading
    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"started": True})

if __name__ == '__main__':
    app.run(port=5050, debug=True)
```

---

## Running the App

### First-time setup
```bash
python main.py --now        # Run pipeline immediately (test it works)
python api/routes.py        # Start dashboard at http://localhost:5050
```

### Daily automated run
```bash
python main.py              # Starts scheduler daemon (runs at 6am daily)
```

### Run only the dashboard (view existing data)
```bash
python api/routes.py
# Open http://localhost:5050
```

---

## Dashboard UI Pages

| Page | What you do there |
|---|---|
| Dashboard | Daily overview — top ideas + stats at a glance |
| Idea Feed | Full ranked list, filter by source, search, sort |
| Saved | Your personal shortlist of ideas to build |
| Scrapers | See status of each data source, run manually |
| Schedule | Enable/disable/edit cron schedules |
| Logs | Real-time pipeline output, error tracking |
| Settings | API keys, subreddit targets, scraper config |

---

## Scoring Formula

Each idea receives 4 sub-scores (0-100) from Claude AI + validation:

```
score_overall = (demand × 0.35) + (opportunity × 0.25) + (trend × 0.25) + (uniqueness × 0.15)
```

Where:
- **demand** = how many people are actively searching / complaining about this problem
- **opportunity** = 100 − competition (low competition = high opportunity)
- **trend** = is interest growing or declining?
- **uniqueness** = how differentiated from existing solutions?

Final score is on a 0-10 scale. Ideas below 6.0 are automatically discarded.

---

## Monthly Cost Estimate

| Service | Plan | Cost |
|---|---|---|
| PRAW (Reddit API) | Free tier | $0 |
| google-play-scraper | Open source | $0 |
| pytrends | Open source | $0 |
| HackerNews Algolia API | 100% free | $0 |
| Product Hunt API | Free developer | $0 |
| Claude API (claude-sonnet-4-6) | ~2M tokens/month | ~$3-6 |
| SerpAPI (optional) | Free 100 searches | $0 |
| **Total** | | **~$3-6/month** |

---

## Extending the App

### Add a new scraper
1. Create `scrapers/new_source_scraper.py` with a `run()` function that returns a list of `{id, source, content, metadata}` dicts
2. Import and add it to the pipeline in `main.py`
3. Add a new scraper card in the dashboard HTML

### Add email digest
1. Add `sendgrid` or `smtplib` to send the top-10 ideas daily
2. Trigger from `main.py` after `save_ideas()` completes

### Deploy to a server (run 24/7)
```bash
# On a $4/month VPS (DigitalOcean, Hetzner)
git clone your-repo && cd ideahunter
cp .env.example .env && nano .env   # Fill in keys
pip install -r requirements.txt
nohup python main.py &              # Background daemon
nohup python api/routes.py &        # Background Flask
```
