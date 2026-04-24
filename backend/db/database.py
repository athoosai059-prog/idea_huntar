import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "ideahunter.db"

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

def mark_posts_processed(post_ids: list[str]):
    if not post_ids:
        return
    with get_conn() as conn:
        placeholders = ",".join("?" * len(post_ids))
        conn.execute(f"UPDATE raw_posts SET processed=1 WHERE id IN ({placeholders})", post_ids)

def save_ideas(ideas: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO ideas
               (name, description, pain_point, source, keywords,
                score_overall, score_demand, score_competition, score_trend, score_uniqueness)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [(i.get("name"), i.get("description"), i.get("pain_point"), i.get("source"),
              json.dumps(i.get("keywords", [])),
              i.get("score_overall"), i.get("score_demand"),
              i.get("score_competition"), i.get("score_trend"), i.get("score_uniqueness"))
             for i in ideas]
        )

def get_all_ideas(min_score=0.0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ideas WHERE score_overall >= ? ORDER BY score_overall DESC",
            (min_score,)
        ).fetchall()
    return [dict(r) for r in rows]

def log_run(source: str, records: int, ideas: int = 0, status: str = "ok", error: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO run_log (source, records_collected, ideas_found, status, error) VALUES (?,?,?,?,?)",
            (source, records, ideas, status, error)
        )
def save_research(idea_id, r_type, content):
    with get_conn() as conn:
        conn.execute("INSERT INTO deep_research (idea_id, type, content) VALUES (?, ?, ?)", 
                    (idea_id, r_type, content))

def get_research(idea_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM deep_research WHERE idea_id = ?", (idea_id,)).fetchall()
        return [dict(r) for r in rows]

def save_demand_metrics(idea_id, search_volume, keyword_difficulty, cpc):
    with get_conn() as conn:
        # Delete existing for this idea to keep only latest, or just insert new ones
        conn.execute("DELETE FROM demand_metrics WHERE idea_id = ?", (idea_id,))
        conn.execute(
            "INSERT INTO demand_metrics (idea_id, search_volume, keyword_difficulty, cpc) VALUES (?, ?, ?, ?)",
            (idea_id, search_volume, keyword_difficulty, cpc)
        )

def get_demand_metrics(idea_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM demand_metrics WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1", (idea_id,)).fetchone()
        return dict(row) if row else None

def save_gsc_metrics(idea_id, impressions, clicks, position, ctr):
    with get_conn() as conn:
        conn.execute("DELETE FROM gsc_metrics WHERE idea_id = ?", (idea_id,))
        conn.execute(
            "INSERT INTO gsc_metrics (idea_id, impressions, clicks, position, ctr) VALUES (?, ?, ?, ?, ?)",
            (idea_id, impressions, clicks, position, ctr)
        )

def get_gsc_metrics(idea_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM gsc_metrics WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1", (idea_id,)).fetchone()
        return dict(row) if row else None

def get_saved_ideas():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM ideas WHERE saved = 1").fetchall()
    return [dict(r) for r in rows]
