import os
import json
import sqlite3
import re
from pathlib import Path
from dotenv import load_dotenv

# Optional Postgres support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_batch
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"))
DB_PATH = Path(__file__).parent.parent.parent / "ideahunter.db"

def validate_sql_identifier(identifier: str) -> bool:
    """Validate that a string is safe to use as SQL identifier."""
    if not identifier or not isinstance(identifier, str):
        return False
    # Only allow alphanumeric characters and underscores
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))

def validate_table_name(table_name: str) -> bool:
    """Validate table name to prevent SQL injection."""
    allowed_tables = {'raw_posts', 'ideas', 'run_log', 'deep_research', 'demand_metrics', 'gsc_metrics'}
    return table_name in allowed_tables

def get_conn():
    if IS_POSTGRES:
        if not HAS_POSTGRES:
            raise ImportError("psycopg2 is required for PostgreSQL. Please install it.")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    if IS_POSTGRES:
        schema_file = "schema_postgres.sql"
    else:
        schema_file = "schema.sql"
    
    schema_path = Path(__file__).parent / schema_file
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(schema_path.read_text())
        else:
            conn.executescript(schema_path.read_text())
    
    # Run migrations for existing databases
    ensure_columns()
    print(f"Database initialized ({'Postgres' if IS_POSTGRES else 'SQLite'}).")

def ensure_columns():
    """Ensure all required columns exist in the ideas table."""
    new_cols = {
        "market_evidence": "TEXT",
        "potential_features": "TEXT",
        "detailed_description": "TEXT",
        "status": "TEXT DEFAULT 'active'",
        "dumbed_at": "DATETIME",
        "source_url": "TEXT",
        "source_urls": "TEXT"  # JSON array of all contributing post URLs
    }
    
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                for col, col_type in new_cols.items():
                    try:
                        cur.execute(f"ALTER TABLE ideas ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    except Exception: pass
        else:
            # SQLite doesn't support ADD COLUMN IF NOT EXISTS easily
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(ideas)")
            existing_cols = [row[1] for row in cursor.fetchall()]
            for col, col_type in new_cols.items():
                if col not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE ideas ADD COLUMN {col} {col_type}")
                    except Exception: pass
            conn.commit()

def save_raw_posts(posts: list[dict]):
    """Save raw posts with input validation and sanitization."""
    if not posts:
        return

    # Validate and sanitize each post
    validated_posts = []
    for post in posts:
        try:
            # Validate required fields
            if not isinstance(post.get('id'), str) or len(post['id'].strip()) == 0 or len(post['id']) > 255:
                continue
            if not isinstance(post.get('source'), str) or len(post['source'].strip()) == 0 or len(post['source']) > 50:
                continue
            if not isinstance(post.get('content'), str) or len(post['content'].strip()) == 0 or len(post['content']) > 10000:
                continue

            # Validate source
            allowed_sources = {'reddit', 'playstore', 'trends', 'hn', 'ph', 'ih', 'twitter'}
            if post['source'].strip() not in allowed_sources:
                continue

            # Sanitize metadata
            metadata = post.get('metadata', {})
            if not isinstance(metadata, dict):
                metadata = {}

            # Limit metadata size
            metadata_json = json.dumps(metadata)
            if len(metadata_json) > 5000:  # 5KB limit
                continue

            validated_post = {
                "id": post['id'][:255],  # Enforce length limit
                "source": post['source'],
                "content": post['content'][:10000],  # Enforce length limit
                "metadata": metadata_json
            }
            validated_posts.append(validated_post)

        except Exception as e:
            # Skip invalid posts rather than failing the entire batch
            continue

    if not validated_posts:
        return

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                execute_batch(cur,
                    "INSERT INTO raw_posts (id, source, content, metadata) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    [(p["id"], p["source"], p["content"], p["metadata"]) for p in validated_posts]
                )
        else:
            conn.executemany(
                "INSERT OR IGNORE INTO raw_posts (id, source, content, metadata) VALUES (?,?,?,?)",
                [(p["id"], p["source"], p["content"], p["metadata"]) for p in validated_posts]
            )
            conn.commit()

def get_unprocessed_posts(limit=500):
    """Get unprocessed posts with input validation."""
    try:
        # Validate and sanitize limit
        limit = int(limit)
        limit = max(1, min(1000, limit))  # Clamp between 1-1000
    except (ValueError, TypeError):
        limit = 500

    query = "SELECT * FROM raw_posts WHERE processed=0 LIMIT %s" if IS_POSTGRES else "SELECT * FROM raw_posts WHERE processed=0 LIMIT ?"
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]

def mark_posts_processed(post_ids: list[str]):
    """Mark posts as processed with input validation."""
    if not post_ids:
        return

    # Validate and sanitize post IDs
    validated_ids = []
    for post_id in post_ids:
        if isinstance(post_id, str) and len(post_id) <= 255:  # Reasonable length limit
            # Only allow alphanumeric, hyphens, and underscores
            if re.match(r'^[a-zA-Z0-9_-]+$', post_id):
                validated_ids.append(post_id)

    if not validated_ids:
        return

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                # Use ANY with parameterized array for PostgreSQL
                cur.execute("UPDATE raw_posts SET processed=1 WHERE id = ANY(%s)", (validated_ids,))
        else:
            # Use proper parameterized query with placeholders for SQLite
            placeholders = ",".join(["?"] * len(validated_ids))
            query = f"UPDATE raw_posts SET processed=1 WHERE id IN ({placeholders})"
            conn.execute(query, validated_ids)
            conn.commit()

def save_ideas(ideas: list[dict]):
    """Save ideas with input validation and sanitization."""
    if not ideas:
        return

    # Validate and sanitize each idea
    validated_ideas = []
    for idea in ideas:
        try:
            # Validate required fields
            if not isinstance(idea.get('name'), str) or len(idea['name'].strip()) == 0 or len(idea['name']) > 200:
                continue
            if not isinstance(idea.get('description'), str) or len(idea['description'].strip()) == 0 or len(idea['description']) > 1000:
                continue

            # Validate optional fields
            pain_point = idea.get('pain_point', '')
            if pain_point and (not isinstance(pain_point, str) or len(pain_point) > 500):
                pain_point = str(pain_point)[:500]

            source = idea.get('source', 'unknown')
            if not isinstance(source, str) or len(source) > 50:
                source = 'unknown'

            # Validate keywords
            keywords = idea.get('keywords', [])
            if not isinstance(keywords, list):
                keywords = []
            # Sanitize keywords
            sanitized_keywords = []
            for kw in keywords[:10]:  # Limit to 10 keywords
                if isinstance(kw, str) and len(kw) <= 100:
                    sanitized_keywords.append(kw)

            # Validate scores
            def validate_score(score, default=50):
                try:
                    score = float(score)
                    return max(0, min(100, score))  # Clamp between 0-100
                except (ValueError, TypeError):
                    return default

            def validate_overall_score(score, default=0):
                try:
                    score = float(score)
                    return max(0, min(10, score))  # Clamp between 0-10
                except (ValueError, TypeError):
                    return default

            validated_idea = {
                "name": idea['name'][:200],
                "description": idea['description'][:1000],
                "detailed_description": idea.get('detailed_description', '')[:5000],
                "pain_point": pain_point,
                "market_evidence": idea.get('market_evidence', ''),
                "potential_features": json.dumps(idea.get('potential_features', [])),
                "source": source,
                "source_url": idea.get('source_url', ''),
                "source_urls": json.dumps(idea.get('source_urls', [])),
                "keywords": json.dumps(sanitized_keywords),
                "score_overall": validate_overall_score(idea.get('score_overall'), 0),
                "score_demand": validate_score(idea.get('score_demand')),
                "score_competition": validate_score(idea.get('score_competition')),
                "score_trend": validate_score(idea.get('score_trend')),
                "score_uniqueness": validate_score(idea.get('score_uniqueness'))
            }
            validated_ideas.append(validated_idea)

        except Exception as e:
            # Skip invalid ideas rather than failing the entire batch
            continue

    # De-duplicate ideas: skip if name+source already exists, OR if source_url already exists
    with get_conn() as conn:
        cursor = conn.cursor()
        final_ideas = []
        for i in validated_ideas:
            is_duplicate = False
            
            # Check by source_url if one exists
            if i.get("source_url"):
                check_query = "SELECT id FROM ideas WHERE source_url = %s" if IS_POSTGRES else "SELECT id FROM ideas WHERE source_url = ?"
                cursor.execute(check_query, (i["source_url"],))
                if cursor.fetchone():
                    is_duplicate = True
            
            if not is_duplicate:
                check_query = "SELECT id FROM ideas WHERE name = %s AND source = %s" if IS_POSTGRES else "SELECT id FROM ideas WHERE name = ? AND source = ?"
                cursor.execute(check_query, (i["name"], i["source"]))
                if cursor.fetchone():
                    is_duplicate = True
            
            if not is_duplicate:
                final_ideas.append(i)
        
    if not final_ideas:
        return

    # Use fixed field names and parameterized queries
    fields = "(name, description, detailed_description, pain_point, market_evidence, potential_features, source, source_url, source_urls, keywords, score_overall, score_demand, score_competition, score_trend, score_uniqueness)"
    placeholders = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" if IS_POSTGRES else "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    query = f"INSERT INTO ideas {fields} VALUES {placeholders}"

    values = [(i["name"], i["description"], i["detailed_description"], i["pain_point"],
               i["market_evidence"], i["potential_features"], i["source"],
               i["source_url"], i["source_urls"],
               i["keywords"], i["score_overall"], i["score_demand"],
               i["score_competition"], i["score_trend"], i["score_uniqueness"])
              for i in final_ideas]

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                execute_batch(cur, query, values)
        else:
            conn.executemany(query, values)
            conn.commit()

def get_all_ideas(min_score=0.0, status='active'):
    """Get ideas filtered by status and score."""
    try:
        min_score = float(min_score)
        min_score = max(0.0, min(10.0, min_score))
    except (ValueError, TypeError):
        min_score = 0.0

    query = f"SELECT * FROM ideas WHERE status = ? AND score_overall >= ? ORDER BY created_at DESC"
    if IS_POSTGRES:
        query = f"SELECT * FROM ideas WHERE status = %s AND score_overall >= %s ORDER BY created_at DESC"
    
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (status, min_score))
                return cur.fetchall()
        else:
            return [dict(row) for row in conn.execute(query, (status, min_score)).fetchall()]

def dumb_idea(idea_id):
    """Move an idea to the dumbed graveyard."""
    query = "UPDATE ideas SET status = 'dumbed', dumbed_at = CURRENT_TIMESTAMP WHERE id = ?"
    if IS_POSTGRES:
        query = "UPDATE ideas SET status = 'dumbed', dumbed_at = CURRENT_TIMESTAMP WHERE id = %s"
    
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id,))
        else:
            conn.execute(query, (idea_id,))
            conn.commit()
    return True

def cleanup_dumbed_ideas(days=7):
    """Permanently delete dumbed ideas older than X days."""
    if IS_POSTGRES:
        query = f"DELETE FROM ideas WHERE status = 'dumbed' AND dumbed_at < NOW() - INTERVAL '{days} days'"
    else:
        query = f"DELETE FROM ideas WHERE status = 'dumbed' AND dumbed_at < datetime('now', '-{days} days')"
    
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query)
        else:
            conn.execute(query)
            conn.commit()
    return True

def log_run(source: str, records: int, ideas: int = 0, status: str = "ok", error: str = None):
    """Log pipeline run with input validation."""
    # Validate source
    allowed_sources = {'reddit', 'playstore', 'trends', 'hn', 'ph', 'ih', 'twitter', 'pipeline_ai'}
    if source not in allowed_sources:
        source = 'unknown'

    # Validate status
    allowed_statuses = {'ok', 'error', 'warning'}
    if status not in allowed_statuses:
        status = 'unknown'

    # Validate numeric values
    try:
        records = int(records)
        ideas = int(ideas)
        if records < 0: records = 0
        if ideas < 0: ideas = 0
    except (ValueError, TypeError):
        records = 0
        ideas = 0

    # Validate error message length
    if error and not isinstance(error, str):
        error = str(error)
    if error and len(error) > 1000:  # Limit error message length
        error = error[:1000]

    # Use fixed query with parameterized values
    placeholders = "(%s,%s,%s,%s,%s)" if IS_POSTGRES else "(?,?,?,?,?)"
    query = f"INSERT INTO run_log (source, records_collected, ideas_found, status, error) VALUES {placeholders}"

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (source, records, ideas, status, error))
        else:
            conn.execute(query, (source, records, ideas, status, error))
            conn.commit()

def save_research(idea_id, r_type, content):
    """Save research data with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return
    except (ValueError, TypeError):
        return

    # Validate research type
    base_types = {'competitors', 'playbook', 'seo_brief', 'growth', 'launch_plan', 'competitor_analysis', 'seo_strategy', 'consensus_plan'}
    # Also allow provider-suffixed types like "consensus_plan_groq", "seo_strategy_gemini", etc.
    is_valid = r_type in base_types or any(r_type.startswith(bt + "_") for bt in base_types)
    if not is_valid:
        return

    # Validate content length
    if not isinstance(content, str) or len(content) > 100000:  # 100KB limit
        return

    # Use fixed query with parameterized values
    placeholders = "(%s, %s, %s)" if IS_POSTGRES else "(?, ?, ?)"
    query = f"INSERT INTO deep_research (idea_id, type, content) VALUES {placeholders}"

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id, r_type, content))
        else:
            conn.execute(query, (idea_id, r_type, content))
            conn.commit()

def get_research(idea_id):
    """Get research data with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return []
    except (ValueError, TypeError):
        return []

    query = "SELECT * FROM deep_research WHERE idea_id = %s" if IS_POSTGRES else "SELECT * FROM deep_research WHERE idea_id = ?"
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id,))
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(query, (idea_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]

def save_demand_metrics(idea_id, search_volume, keyword_difficulty, cpc):
    """Save demand metrics with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return
    except (ValueError, TypeError):
        return

    # Validate and sanitize metrics
    try:
        search_volume = max(0, int(search_volume))
        keyword_difficulty = max(0, min(100, int(keyword_difficulty)))
        cpc = max(0.0, float(cpc))
    except (ValueError, TypeError):
        return

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM demand_metrics WHERE idea_id = %s", (idea_id,))
                cur.execute(
                    "INSERT INTO demand_metrics (idea_id, search_volume, keyword_difficulty, cpc) VALUES (%s, %s, %s, %s)",
                    (idea_id, search_volume, keyword_difficulty, cpc)
                )
        else:
            conn.execute("DELETE FROM demand_metrics WHERE idea_id = ?", (idea_id,))
            conn.execute(
                "INSERT INTO demand_metrics (idea_id, search_volume, keyword_difficulty, cpc) VALUES (?, ?, ?, ?)",
                (idea_id, search_volume, keyword_difficulty, cpc)
            )
            conn.commit()

def get_demand_metrics(idea_id):
    """Get demand metrics with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return None
    except (ValueError, TypeError):
        return None

    query = "SELECT * FROM demand_metrics WHERE idea_id = %s ORDER BY created_at DESC LIMIT 1" if IS_POSTGRES else "SELECT * FROM demand_metrics WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1"
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id,))
                row = cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(query, (idea_id,))
            row = cur.fetchone()
        return dict(row) if row else None

def save_gsc_metrics(idea_id, impressions, clicks, position, ctr):
    """Save Google Search Console metrics with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return
    except (ValueError, TypeError):
        return

    # Validate and sanitize metrics
    try:
        impressions = max(0, int(impressions))
        clicks = max(0, int(clicks))
        position = max(0.0, float(position))
        ctr = max(0.0, min(100.0, float(ctr)))  # CTR should be 0-100%
    except (ValueError, TypeError):
        return

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM gsc_metrics WHERE idea_id = %s", (idea_id,))
                cur.execute(
                    "INSERT INTO gsc_metrics (idea_id, impressions, clicks, position, ctr) VALUES (%s, %s, %s, %s, %s)",
                    (idea_id, impressions, clicks, position, ctr)
                )
        else:
            conn.execute("DELETE FROM gsc_metrics WHERE idea_id = ?", (idea_id,))
            conn.execute(
                "INSERT INTO gsc_metrics (idea_id, impressions, clicks, position, ctr) VALUES (?, ?, ?, ?, ?)",
                (idea_id, impressions, clicks, position, ctr)
            )
            conn.commit()

def get_gsc_metrics(idea_id):
    """Get Google Search Console metrics with input validation."""
    try:
        # Validate idea_id
        idea_id = int(idea_id)
        if idea_id <= 0:
            return None
    except (ValueError, TypeError):
        return None

    query = "SELECT * FROM gsc_metrics WHERE idea_id = %s ORDER BY created_at DESC LIMIT 1" if IS_POSTGRES else "SELECT * FROM gsc_metrics WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1"
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id,))
                row = cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(query, (idea_id,))
            row = cur.fetchone()
        return dict(row) if row else None

def get_saved_ideas():
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ideas WHERE saved = 1")
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ideas WHERE saved = 1")
            rows = cur.fetchall()
    return [dict(r) for r in rows]

def toggle_idea_saved(idea_id):
    """Toggle idea saved status with input validation."""
    try:
        # Validate that idea_id is an integer
        idea_id = int(idea_id)
        if idea_id <= 0:
            return False, False
    except (ValueError, TypeError):
        return False, False

    query_select = "SELECT saved FROM ideas WHERE id=%s" if IS_POSTGRES else "SELECT saved FROM ideas WHERE id=?"
    query_update = "UPDATE ideas SET saved=%s WHERE id=%s" if IS_POSTGRES else "UPDATE ideas SET saved=? WHERE id=?"

    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query_select, (idea_id,))
                row = cur.fetchone()
                if row:
                    new_status = 1 if row['saved'] == 0 else 0
                    cur.execute(query_update, (new_status, idea_id))
                    return True, bool(new_status)
        else:
            cur = conn.cursor()
            cur.execute(query_select, (idea_id,))
            row = cur.fetchone()
            if row:
                new_status = 1 if row['saved'] == 0 else 0
                cur.execute(query_update, (new_status, idea_id))
                conn.commit()
                return True, bool(new_status)
    return False, False

def get_idea_by_id(idea_id):
    """Get idea by ID with input validation."""
    try:
        # Validate that idea_id is an integer
        idea_id = int(idea_id)
        if idea_id <= 0:
            return None
    except (ValueError, TypeError):
        return None

    query = "SELECT * FROM ideas WHERE id = %s" if IS_POSTGRES else "SELECT * FROM ideas WHERE id = ?"
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, (idea_id,))
                row = cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(query, (idea_id,))
            row = cur.fetchone()
        return dict(row) if row else None

def get_dashboard_stats():
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as c FROM ideas")
                total = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM ideas WHERE score_overall >= 8")
                high = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM ideas WHERE saved=1")
                saved = cur.fetchone()['c']
                cur.execute("SELECT MAX(run_at) as m FROM run_log")
                last_run = cur.fetchone()['m']
                cur.execute("""
                    SELECT source, status, records_collected, ideas_found, run_at 
                    FROM run_log 
                    WHERE id IN (SELECT MAX(id) FROM run_log GROUP BY source)
                """)
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as c FROM ideas")
            total = cur.fetchone()['c']
            cur.execute("SELECT COUNT(*) as c FROM ideas WHERE score_overall >= 8")
            high = cur.fetchone()['c']
            cur.execute("SELECT COUNT(*) as c FROM ideas WHERE saved=1")
            saved = cur.fetchone()['c']
            cur.execute("SELECT MAX(run_at) as m FROM run_log")
            last_run = cur.fetchone()['m']
            cur.execute("""
                SELECT source, status, records_collected, ideas_found, run_at 
                FROM run_log 
                WHERE id IN (SELECT MAX(id) FROM run_log GROUP BY source)
            """)
            rows = cur.fetchall()
            
    scrapers = {}
    for r in rows:
        scrapers[r['source']] = {
            "status": r['status'],
            "records": r['records_collected'],
            "ideas": r['ideas_found'],
            "last_run": r['run_at']
        }
        
    return {
        "total": total,
        "high_score": high,
        "saved": saved,
        "last_run": last_run,
        "scrapers": scrapers
    }

def update_idea_scores(idea_id: int, updated_idea: dict):
    """Update scores for a specific idea after manual validation."""
    try:
        idea_id = int(idea_id)
    except (ValueError, TypeError):
        return False
        
    query = """
        UPDATE ideas 
        SET score_demand = %s, score_competition = %s, score_trend = %s, score_uniqueness = %s, score_overall = %s
        WHERE id = %s
    """ if IS_POSTGRES else """
        UPDATE ideas 
        SET score_demand = ?, score_competition = ?, score_trend = ?, score_uniqueness = ?, score_overall = ?
        WHERE id = ?
    """
    
    values = (
        updated_idea.get('score_demand', 50),
        updated_idea.get('score_competition', 50),
        updated_idea.get('score_trend', 50),
        updated_idea.get('score_uniqueness', 50),
        updated_idea.get('score_overall', 5.0),
        idea_id
    )
    
    with get_conn() as conn:
        if IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(query, values)
        else:
            conn.execute(query, values)
            conn.commit()
    return True

