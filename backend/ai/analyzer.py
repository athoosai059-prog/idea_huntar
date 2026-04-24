import anthropic
import google.generativeai as genai
import json
import logging
from backend.config import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a startup idea miner. Your goal is to convert raw posts/reviews into structured business opportunities.
For each post, output a JSON object with:
- name: Catchy startup name
- description: 1-2 sentence pitch
- pain_point: The specific problem identified
- score_demand: 1-100 (how much people want this)
- score_competition: 1-100 (how many tools already exist)
- score_trend: 1-100 (is this a rising topic?)
- uniqueness: 1-100 (is it a new angle?)
- keywords: List of 3 SEO keywords

Output ONLY a JSON array of these objects."""

def _analyze_with_anthropic(batch_text):
    if not settings.ANTHROPIC_API_KEY:
        raise Exception("Anthropic API Key missing")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze these posts: {batch_text}"}]
    )
    return message.content[0].text

def _analyze_with_gemini(batch_text):
    if not settings.GEMINI_API_KEY:
        raise Exception("Gemini API Key missing")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(f"Analyze these posts: {batch_text}")
    return response.text

def analyze_batch(posts):
    batch_text = "\n---\n".join([f"Source: {p['source']}\nContent: {p['content']}" for p in posts])
    
    # Logic to try primary and fallback to secondary
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    
    last_error = ""
    for ai_provider in order:
        try:
            log.info(f"Using {ai_provider} for analysis...")
            if ai_provider == "anthropic":
                raw_response = _analyze_with_anthropic(batch_text)
            else:
                raw_response = _analyze_with_gemini(batch_text)
                
            # Clean response (strip markdown)
            raw_response = raw_response.strip()
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                 raw_response = raw_response.split("```")[1].split("```")[0].strip()
            
            ideas = json.loads(raw_response)
            # Add metadata from original posts (link back to first post in batch for ref)
            for i in ideas:
                i["source"] = posts[0]["source"]
                i["source_ref"] = posts[0].get("source_id", "")
                # Heuristic overall score
                i["score_overall"] = round((i["score_demand"]*0.4 + (100-i["score_competition"])*0.3 + i["score_trend"]*0.2 + i["uniqueness"]*0.1) / 10, 1)
            return ideas
        except Exception as e:
            log.warning(f"{ai_provider} failed: {e}")
            last_error = str(e)
            continue
            
    raise Exception(f"All AI providers failed. Last error: {last_error}")

def run_analysis(posts, batch_size=10):
    all_ideas = []
    for i in range(0, len(posts), batch_size):
        batch = posts[i:i+batch_size]
        try:
            ideas = analyze_batch(batch)
            all_ideas.extend(ideas)
        except Exception as e:
            log.error(f"Batch failed: {e}")
    return all_ideas
def generate_competitors(idea):
    prompt = f"Analyze competitors for this startup idea: {idea['name']} - {idea['description']}. Target pain point: {idea['pain_point']}. Identify 3-5 existing tools and explain their weaknesses compared to our solution. Output in clean Markdown."
    
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    for ai in order:
        try:
            if ai == "gemini": return _analyze_with_gemini(prompt)
            else: return _analyze_with_anthropic(prompt)
        except: continue
    return "Failed to generate competitor analysis."

def generate_playbook(idea):
    prompt = f"Create a 30-day launch playbook for this startup idea: {idea['name']} - {idea['description']}. Include: Day 1-7 (Foundation), Day 8-14 (Build), Day 15-21 (Beta), Day 22-30 (Launch). Also suggest 3 specific niche communities to launch on. Output in clean Markdown."
    
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    for ai in order:
        try:
            if ai == "gemini": return _analyze_with_gemini(prompt)
            else: return _analyze_with_anthropic(prompt)
        except: continue
    return "Failed to generate launch playbook."

def generate_seo_brief(idea):
    prompt = f"""Generate a comprehensive SEO and Content Brief for this startup idea: {idea['name']} - {idea['description']}.
    Target Keyword: {idea['name']} (and related niche keywords).
    
    Output MUST include:
    1. **Meta Strategy**: Page Title (max 60 chars), Meta Description (max 160 chars), and URL Slug.
    2. **On-Page Hierarchy**: Optimized H1 and H2 structure.
    3. **Content Piece**: A 200-word authoritative 'About' description for the tool.
    4. **FAQ Section**: 4 common questions and detailed answers for user search intent.
    5. **JSON-LD Schema**: A complete, valid FAQPage or SoftwareApplication JSON-LD block ready to paste.
    
    Output in clean Markdown."""
    
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    for ai in order:
        try:
            if ai == "gemini": return _analyze_with_gemini(prompt)
            else: return _analyze_with_anthropic(prompt)
        except: continue
    return "Failed to generate SEO brief."

def generate_growth_suggestions(idea, gsc_metrics):
    prompt = f"""Act as a Senior SEO Consultant. 
    Startup: {idea['name']} - {idea['description']}
    Current Performance (GSC): {gsc_metrics['impressions']} impressions, {gsc_metrics['clicks']} clicks, Avg Position {gsc_metrics['position']}.
    
    This page is 'Almost There' (Position 5-20). Provide 3 specific, high-impact 'Growth Hacks' to push it to Position 1.
    Suggestions should focus on internal linking, content expansion, or technical metadata tweaks.
    Output in clean Markdown."""
    
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    for ai in order:
        try:
            if ai == "gemini": return _analyze_with_gemini(prompt)
            else: return _analyze_with_anthropic(prompt)
        except: continue
    return "Failed to generate growth suggestions."
