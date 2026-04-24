from flask import Flask, jsonify, request, send_from_directory
from backend.db.database import get_all_ideas, get_conn
import json
import os
from pathlib import Path

app = Flask(__name__)

# Base directory for frontend files
BASE_DIR = Path(__file__).parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

@app.route('/api/ideas')
def ideas():
    min_score = float(request.args.get('min_score', 0))
    source = request.args.get('source')
    ideas_list = get_all_ideas(min_score)
    if source and source != 'all':
        ideas_list = [i for i in ideas_list if i['source'] == source]
    
    # Process keywords and ranks
    for idx, i in enumerate(ideas_list):
        if isinstance(i.get('keywords'), str):
            try:
                i['keywords'] = json.loads(i['keywords'])
            except:
                i['keywords'] = []
        i['rank'] = idx + 1
        # Map source labels and classes for frontend
        source_map = {
            'reddit': ('Reddit', 'tag-reddit'),
            'playstore': ('Play Store', 'tag-playstore'),
            'trends': ('Google Trends', 'tag-trends'),
            'hn': ('HackerNews', 'tag-hn'),
            'producthunt': ('Product Hunt', 'tag-producthunt'),
            'ih': ('IndieHackers', 'tag-ih'),
            'twitter': ('Twitter', 'tag-twitter')
        }
        label, cls = source_map.get(i['source'], (i['source'].capitalize(), ''))
        i['sourceLabel'] = label
        i['tagClass'] = cls
        
    return jsonify(ideas_list)

@app.route('/api/ideas/<int:idea_id>/save', methods=['POST'])
def toggle_save(idea_id):
    with get_conn() as conn:
        row = conn.execute("SELECT saved FROM ideas WHERE id=?", (idea_id,)).fetchone()
        if row:
            new_status = 1 if row['saved'] == 0 else 0
            conn.execute("UPDATE ideas SET saved=? WHERE id=?", (new_status, idea_id))
            return jsonify({"ok": True, "saved": bool(new_status)})
    return jsonify({"ok": False, "error": "Idea not found"}), 404

@app.route('/api/stats')
def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM ideas WHERE score_overall >= 8").fetchone()[0]
        saved = conn.execute("SELECT COUNT(*) FROM ideas WHERE saved=1").fetchone()[0]
        last_run = conn.execute("SELECT MAX(run_at) FROM run_log").fetchone()[0]
    # Get scraper specific stats
    scrapers = {}
    with get_conn() as conn:
        # Get latest status for each scraper
        rows = conn.execute("""
            SELECT source, status, records_collected, ideas_found, run_at 
            FROM run_log 
            WHERE id IN (SELECT MAX(id) FROM run_log GROUP BY source)
        """).fetchall()
        for r in rows:
            scrapers[r['source']] = {
                "status": r['status'],
                "records": r['records_collected'],
                "ideas": r['ideas_found'],
                "last_run": r['run_at']
            }

    return jsonify({
        "total": total, 
        "high_score": high, 
        "saved": saved, 
        "last_run": last_run or "Never",
        "scrapers": scrapers
    })

@app.route('/api/run', methods=['POST'])
def trigger_run():
    from backend.main import run_pipeline
    import threading
    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"started": True})

from backend.config import settings, env_path
from dotenv import set_key

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        data = request.json
        # Update .env file
        if 'anthropic_key' in data: set_key(str(env_path), "ANTHROPIC_API_KEY", data['anthropic_key'])
        if 'gemini_key' in data: set_key(str(env_path), "GEMINI_API_KEY", data['gemini_key'])
        if 'primary_ai' in data: set_key(str(env_path), "PRIMARY_AI", data['primary_ai'])
        if 'min_score' in data: set_key(str(env_path), "MIN_IDEA_SCORE", str(data['min_score']))
        if 'target_keywords' in data: set_key(str(env_path), "TARGET_KEYWORDS", data['target_keywords'])
        
        # Reload settings in memory
        settings.reload()
        return jsonify({"ok": True})
    
    return jsonify({
        "anthropic_key": settings.ANTHROPIC_API_KEY,
        "gemini_key": settings.GEMINI_API_KEY,
        "primary_ai": settings.PRIMARY_AI,
        "min_score": settings.MIN_IDEA_SCORE,
        "target_keywords": settings.TARGET_KEYWORDS
    })

from backend.ai.analyzer import generate_competitors, generate_playbook, generate_seo_brief, generate_growth_suggestions
from backend.db.database import save_research, get_research, get_demand_metrics, get_gsc_metrics

@app.route('/api/ideas/<int:idea_id>/research', methods=['GET', 'POST'])
def handle_research(idea_id):
    if request.method == 'POST':
        data = request.json
        r_type = data.get('type') # 'competitors' or 'playbook'
        
        # Get idea from DB
        with get_conn() as conn:
            idea = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
            if not idea: return jsonify({"error": "Idea not found"}), 404
            idea = dict(idea)
            
        if r_type == 'competitors':
            content = generate_competitors(idea)
        elif r_type == 'playbook':
            content = generate_playbook(idea)
        elif r_type == 'seo_brief':
            content = generate_seo_brief(idea)
        elif r_type == 'growth':
            gsc = get_gsc_metrics(idea_id)
            if not gsc: return jsonify({"error": "No GSC data found"}), 400
            content = generate_growth_suggestions(idea, gsc)
        else:
            return jsonify({"error": "Invalid research type"}), 400
            
        save_research(idea_id, r_type, content)
        return jsonify({"ok": True, "content": content})
    
    # GET existing research
    results = get_research(idea_id)
    return jsonify(results)

@app.route('/api/ideas/<int:idea_id>/metrics', methods=['GET'])
def get_idea_metrics(idea_id):
    demand = get_demand_metrics(idea_id)
    gsc = get_gsc_metrics(idea_id)
    return jsonify({
        "demand": demand,
        "gsc": gsc
    })

if __name__ == '__main__':
    # Ensure database is initialized
    from backend.db.database import init_db
    init_db()
    app.run(port=5050, debug=True)
