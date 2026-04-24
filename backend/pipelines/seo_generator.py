import logging
from backend.config import settings
from backend.ai.analyzer import _analyze_with_gemini, _analyze_with_anthropic

log = logging.getLogger(__name__)

def generate_seo_brief(idea):
    """
    Generates a complete SEO plan for a specific tool idea.
    """
    log.info(f"Generating SEO Brief for idea: {idea['name']}")
    
    prompt = f"""
    Create a complete SEO plan and brief for this SaaS/Tool idea:
    Name: {idea['name']}
    Description: {idea['description']}
    Pain Point Solved: {idea['pain_point']}
    Target Keywords: {idea.get('keywords', [])}
    
    Please provide the output in clean, well-structured Markdown format including:
    1. **Primary Target Keyword & Secondary Keywords**
    2. **Optimized Meta Title** (under 60 chars)
    3. **Optimized Meta Description** (under 160 chars)
    4. **URL Slug Recommendation**
    5. **H1 and H2 Structure** (Outline for the landing page)
    6. **FAQ Section** (3-4 common questions with concise, SEO-optimized answers)
    7. **Schema Markup recommendation** (e.g., SoftwareApplication schema)
    """
    
    order = ["gemini", "anthropic"] if settings.PRIMARY_AI == "gemini" else ["anthropic", "gemini"]
    for ai_provider in order:
        try:
            if ai_provider == "gemini":
                return _analyze_with_gemini(prompt)
            else:
                return _analyze_with_anthropic(prompt)
        except Exception as e:
            log.warning(f"SEO Brief generation failed with {ai_provider}: {e}")
            continue
            
    return "Failed to generate SEO brief. Please check your API keys."
