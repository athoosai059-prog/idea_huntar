from flask import Flask, jsonify, request, send_from_directory
from backend.db.database import (
    get_all_ideas, get_idea_by_id, toggle_idea_saved, get_saved_ideas,
    get_dashboard_stats, save_ideas, get_research, save_research,
    get_demand_metrics, save_demand_metrics, get_gsc_metrics, save_gsc_metrics
)
import json
import os
import re
from pathlib import Path
from functools import wraps

app = Flask(__name__)

# Base directory for frontend files
BASE_DIR = Path(__file__).parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Input validation helpers
def validate_string(value, max_length=255, min_length=0, pattern=None):
    """Validate and sanitize string input."""
    if not isinstance(value, str):
        return None

    # Trim whitespace
    value = value.strip()

    # Check length
    if len(value) < min_length or len(value) > max_length:
        return None

    # Check pattern if provided
    if pattern and not re.match(pattern, value):
        return None

    return value

def validate_number(value, min_val=None, max_val=None, default=None):
    """Validate and sanitize numeric input."""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return default
        if max_val is not None and num > max_val:
            return default
        return num
    except (ValueError, TypeError):
        return default

def validate_json(value, max_size=10000):
    """Validate JSON input size and structure."""
    if not isinstance(value, dict):
        return None

    # Check JSON size
    json_str = json.dumps(value)
    if len(json_str) > max_size:
        return None

    return value

def sanitize_html(text):
    """Basic HTML sanitization to prevent XSS."""
    if not isinstance(text, str):
        return ""

    # Remove dangerous HTML tags and attributes
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'on\w+\s*=',
        r'javascript:',
        r'vbscript:',
        r'data:',
    ]

    sanitized = text
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

    return sanitized

def validate_idea_id(idea_id):
    """Validate idea ID parameter."""
    try:
        idea_id = int(idea_id)
        if idea_id <= 0:
            return None
        return idea_id
    except (ValueError, TypeError):
        return None

def error_response(message, status_code=400):
    """Standardized error response."""
    return jsonify({
        "error": message,
        "status": "error"
    }), status_code

def validate_request_data(required_fields=None, optional_fields=None, max_size=10000):
    """Decorator to validate request data."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not request.is_json:
                return error_response("Request must be JSON", 400)

            data = request.get_json()

            # Validate JSON size
            json_str = json.dumps(data)
            if len(json_str) > max_size:
                return error_response("Request payload too large", 413)

            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)

            # Sanitize string fields
            if data:
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = sanitize_html(value.strip())

            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

@app.route('/api/ideas')
def ideas():
    """Get ideas with input validation."""
    try:
        # Validate and sanitize min_score parameter
        min_score = validate_number(
            request.args.get('min_score', 0),
            min_val=0.0,
            max_val=10.0,
            default=0.0
        )

        # Validate source parameter
        source = request.args.get('source')
        allowed_sources = {'all', 'reddit', 'playstore', 'trends', 'hn', 'producthunt', 'ih', 'twitter'}
        if source and source not in allowed_sources:
            return error_response("Invalid source parameter", 400)

        # Validate status parameter
        status = request.args.get('status', 'active')
        if status not in {'active', 'dumbed'}:
            status = 'active'

        ideas_list = get_all_ideas(min_score, status=status)

        # Filter by source if specified
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

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/ideas/<int:idea_id>/save', methods=['POST'])
def toggle_save(idea_id):
    """Toggle idea saved status with validation."""
    try:
        # Validate idea_id
        validated_id = validate_idea_id(idea_id)
        if not validated_id:
            return error_response("Invalid idea ID", 400)

        from backend.db.database import toggle_idea_saved
        success, saved_status = toggle_idea_saved(validated_id)

        if success:
            return jsonify({"ok": True, "saved": saved_status})
        return error_response("Idea not found", 404)

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/ideas/<int:idea_id>/validate', methods=['POST'])
def validate_idea(idea_id):
    """Manually validate an idea."""
    try:
        validated_id = validate_idea_id(idea_id)
        if not validated_id:
            return error_response("Invalid idea ID", 400)
            
        from backend.db.database import get_idea_by_id, update_idea_scores
        idea = get_idea_by_id(validated_id)
        if not idea:
            return error_response("Idea not found", 404)
            
        from backend.validators.validator import validate_ideas
        validated_ideas = validate_ideas([dict(idea)])
        if validated_ideas:
            validated_idea = validated_ideas[0]
            update_idea_scores(validated_id, validated_idea)
            return jsonify({"ok": True, "idea": validated_idea})
            
        return error_response("Validation failed", 500)
    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/ideas/custom', methods=['POST'])
@validate_request_data(required_fields=['name', 'description'])
def add_custom_idea():
    """Add a custom user idea."""
    try:
        data = request.get_json()
        from backend.db.database import save_ideas, get_conn, IS_POSTGRES
        
        custom_idea = {
            "name": sanitize_html(data['name']),
            "description": sanitize_html(data['description']),
            "pain_point": sanitize_html(data.get('pain_point', 'Custom user idea')),
            "source": "custom",
            "score_demand": 50,
            "score_competition": 50,
            "score_trend": 50,
            "score_uniqueness": 80,
            "score_overall": 6.0,
            "keywords": data.get('keywords', [])
        }
        
        # save_ideas requires a list of dicts, and validates them
        save_ideas([custom_idea])
        
        # Now mark it as saved (shortlisted)
        with get_conn() as conn:
            query = "UPDATE ideas SET saved = 1 WHERE source = 'custom' AND name = %s" if IS_POSTGRES else "UPDATE ideas SET saved = 1 WHERE source = 'custom' AND name = ?"
            if IS_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(query, (custom_idea['name'],))
            else:
                conn.execute(query, (custom_idea['name'],))
                conn.commit()
                
        return jsonify({"ok": True, "message": "Custom idea added successfully"})
    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/stats')
def stats():
    """Get dashboard statistics."""
    try:
        from backend.db.database import get_dashboard_stats
        stats_data = get_dashboard_stats()
        return jsonify(stats_data)
    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/run', methods=['POST'])
def trigger_run():
    """Trigger pipeline run with validation."""
    try:
        # Validate that this is a POST request
        if request.method != 'POST':
            return error_response("Method not allowed", 405)

        from backend.main import run_pipeline
        import threading

        # Run pipeline in background thread
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        return jsonify({"started": True, "message": "Pipeline started successfully"})

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

from backend.config import settings, env_path
from dotenv import set_key

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Handle settings with validation."""
    try:
        if request.method == 'POST':
            if not request.is_json:
                return error_response("Request must be JSON", 400)

            data = request.get_json()

            # Validate and sanitize each setting
            if 'anthropic_key' in data:
                key = validate_string(data['anthropic_key'], max_length=200)
                if key:
                    set_key(str(env_path), "ANTHROPIC_API_KEY", key)

            if 'gemini_key' in data:
                key = validate_string(data['gemini_key'], max_length=200)
                if key:
                    set_key(str(env_path), "GEMINI_API_KEY", key)
                    
            if 'groq_key' in data:
                key = validate_string(data['groq_key'], max_length=200)
                if key:
                    set_key(str(env_path), "GROQ_API_KEY", key)
                    
            if 'together_key' in data:
                key = validate_string(data['together_key'], max_length=200)
                if key:
                    set_key(str(env_path), "TOGETHER_API_KEY", key)
                    
            if 'cerebras_key' in data:
                key = validate_string(data['cerebras_key'], max_length=200)
                if key:
                    set_key(str(env_path), "CEREBRAS_API_KEY", key)

            if 'primary_ai' in data:
                ai = validate_string(data['primary_ai'], max_length=20)
                if ai in ['anthropic', 'gemini', 'groq', 'together', 'cerebras']:
                    set_key(str(env_path), "PRIMARY_AI", ai)

            if 'min_score' in data:
                score = validate_number(data['min_score'], min_val=0.0, max_val=10.0)
                if score is not None:
                    set_key(str(env_path), "MIN_IDEA_SCORE", str(score))

            if 'target_keywords' in data:
                keywords = validate_string(data['target_keywords'], max_length=500)
                if keywords is not None:
                    set_key(str(env_path), "TARGET_KEYWORDS", keywords)

            # Reload settings in memory
            settings.reload()
            return jsonify({"ok": True, "message": "Settings updated successfully"})

        return jsonify({
            "anthropic_key": settings.ANTHROPIC_API_KEY[:10] + "..." if settings.ANTHROPIC_API_KEY else "",
            "gemini_key": settings.GEMINI_API_KEY[:10] + "..." if settings.GEMINI_API_KEY else "",
            "groq_key": settings.GROQ_API_KEY[:10] + "..." if settings.GROQ_API_KEY else "",
            "together_key": settings.TOGETHER_API_KEY[:10] + "..." if settings.TOGETHER_API_KEY else "",
            "cerebras_key": settings.CEREBRAS_API_KEY[:10] + "..." if settings.CEREBRAS_API_KEY else "",
            "primary_ai": settings.PRIMARY_AI,
            "min_score": settings.MIN_IDEA_SCORE,
            "target_keywords": settings.TARGET_KEYWORDS
        })

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

from backend.db.database import save_research, get_research, get_demand_metrics, get_gsc_metrics

@app.route('/api/ideas/<int:idea_id>/research', methods=['GET', 'POST'])
def handle_research(idea_id):
    """Handle research requests with validation."""
    try:
        # Validate idea_id
        validated_id = validate_idea_id(idea_id)
        if not validated_id:
            return error_response("Invalid idea ID", 400)

        if request.method == 'POST':
            if not request.is_json:
                return error_response("Request must be JSON", 400)

            data = request.get_json()
            r_type = data.get('type')

            # Validate research type
            allowed_types = {'launch_plan'}
            if r_type not in allowed_types:
                return error_response(f"Invalid research type. Must be one of: {', '.join(allowed_types)}", 400)

            # Get idea from DB
            from backend.db.database import get_idea_by_id
            idea = get_idea_by_id(validated_id)
            if not idea:
                return error_response("Idea not found", 404)

            # Generate content based on type
            if r_type == 'launch_plan':
                from backend.ai.analyzer import generate_launch_plan
                content = generate_launch_plan(idea)
            else:
                return error_response("Invalid research type", 400)

            # Sanitize content
            if isinstance(content, str):
                content = sanitize_html(content)

            save_research(validated_id, r_type, content)
            return jsonify({"ok": True, "content": content})

        # GET request - return existing research
        results = get_research(validated_id)
        return jsonify(results)

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

@app.route('/api/ideas/<int:idea_id>/metrics', methods=['GET'])
def get_idea_metrics(idea_id):
    """Get idea metrics with validation."""
    try:
        # Validate idea_id
        validated_id = validate_idea_id(idea_id)
        if not validated_id:
            return error_response("Invalid idea ID", 400)

        demand = get_demand_metrics(validated_id)
        gsc = get_gsc_metrics(validated_id)

        return jsonify({
            "demand": demand,
            "gsc": gsc
        })

    except Exception as e:
        return error_response(f"Internal server error: {str(e)}", 500)

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'IdeaHunter API is running'})

# Get individual idea by ID
@app.route('/api/ideas/<int:idea_id>')
def get_idea(idea_id):
    """Get individual idea by ID with validation."""
    try:
        idea = get_idea_by_id(idea_id)
        if idea is None:
            return error_response("Idea not found", 404)
        return jsonify({'idea': idea})
    except Exception as e:
        return error_response(f"Error retrieving idea: {str(e)}", 500)

# Toggle idea saved status
@app.route('/api/ideas/<int:idea_id>/toggle-saved', methods=['POST'])
def toggle_saved(idea_id):
    """Toggle idea saved status."""
    try:
        success, saved_status = toggle_idea_saved(idea_id)
        if success:
            return jsonify({'success': True, 'saved': saved_status})
        else:
            return error_response("Failed to toggle saved status", 500)
    except Exception as e:
        return error_response(f"Error toggling saved status: {str(e)}", 500)


@app.route('/api/ideas/<int:idea_id>/dumb', methods=['POST'])
def dumb_idea_route(idea_id):
    db.dumb_idea(idea_id)
    return jsonify({"ok": True})

@app.route('/api/graveyard', methods=['GET'])
def get_graveyard():
    ideas = db.get_all_ideas(status='dumbed')
    return jsonify(ideas)

@app.route('/api/graveyard/cleanup', methods=['POST'])
def cleanup_graveyard():
    db.cleanup_dumbed_ideas(days=7)
    return jsonify({"ok": True})

# Get saved ideas
@app.route('/api/ideas/saved')
def saved_ideas():
    """Get all saved ideas."""
    try:
        ideas = get_saved_ideas()
        return jsonify({'ideas': ideas})
    except Exception as e:
        return error_response(f"Error retrieving saved ideas: {str(e)}", 500)

# Dashboard statistics
@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics."""
    try:
        stats = get_dashboard_stats()
        return jsonify({'stats': stats})
    except Exception as e:
        return error_response(f"Error retrieving dashboard stats: {str(e)}", 500)

# Save new ideas
@app.route('/api/ideas', methods=['POST'])
def create_ideas():
    """Create new ideas with validation."""
    try:
        data = request.get_json()
        if not data or 'ideas' not in data:
            return error_response("Missing 'ideas' in request body", 400)

        ideas = data['ideas']
        if not isinstance(ideas, list):
            return error_response("'ideas' must be an array", 400)

        # Validate and save ideas
        save_ideas(ideas)
        return jsonify({'success': True, 'message': f'Saved {len(ideas)} ideas'})
    except Exception as e:
        return error_response(f"Error saving ideas: {str(e)}", 500)

# Global error handlers
@app.errorhandler(400)
def bad_request(error):
    return error_response("Bad request", 400)

@app.errorhandler(404)
def not_found(error):
    return error_response("Resource not found", 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return error_response("Method not allowed", 405)

@app.errorhandler(413)
def payload_too_large(error):
    return error_response("Request payload too large", 413)

@app.errorhandler(500)
def internal_error(error):
    return error_response("Internal server error", 500)

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions."""
    return error_response(f"An unexpected error occurred: {str(error)}", 500)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"
    return response

if __name__ == '__main__':
    # Ensure database is initialized
    from backend.db.database import init_db
    init_db()
    app.run(port=5050, debug=True)
