import anthropic
from google import genai
import groq
from openai import OpenAI
import json
from backend.config import settings
from backend.utils.logging_config import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are an elite Startup Opportunity Analyst. Your goal is to convert raw posts, reviews, and discussions into professional, highly-detailed business opportunities.

For each relevant post, output a JSON object with:
- name: A catchy, professional startup name.
- description: A clear, professional 2-3 sentence pitch.
- detailed_description: A deep dive (100-150 words) into the market opportunity, why it exists, and how it solves the identified pain point.
- pain_point: The specific, core problem identified in the text.
- market_evidence: A summary of what real people are saying in the text. Include direct insights, frustrations, or specific quotes where possible.
- potential_features: A list of 3-5 core features or 'must-haves' that users are asking for.
- score_demand: 1-100 (how urgent/desirable is this solution?)
- score_competition: 1-100 (how many tools already exist? 100 = very crowded)
- score_trend: 1-100 (is this topic gaining momentum?)
- uniqueness: 1-100 (is it a new angle or a better version of something old?)
- keywords: List of 5 SEO keywords related to the niche.
- source: The exact source platform string from the post (e.g. 'reddit', 'hn', 'twitter', 'ih', 'producthunt', 'trends').

Output ONLY a JSON array of these objects. If a post is not a business opportunity, skip it."""

def _analyze_with_anthropic(batch_text):
    """Analyze batch using Anthropic Claude."""
    if not settings.ANTHROPIC_API_KEY:
        raise Exception("Anthropic API Key missing")

    log.debug("Using Anthropic Claude for analysis...")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}]
    )
    return message.content[0].text

def _analyze_with_gemini(batch_text):
    """Analyze batch using Google Gemini (new google.genai SDK)."""
    if not settings.GEMINI_API_KEY:
        raise Exception("Gemini API Key missing")

    log.debug("Using Google Gemini for analysis...")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
    
    response = client.models.generate_content(
        model=model_name,
        contents=f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}",
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=4096,
        ),
    )
    return response.text

def _analyze_with_groq(batch_text):
    """Analyze batch using Groq (free, fast Llama 3.3 70B)."""
    if not settings.GROQ_API_KEY:
        raise Exception("Groq API Key missing")

    log.debug("Using Groq (Llama 3.3 70B) for analysis...")
    client = groq.Groq(api_key=settings.GROQ_API_KEY)
    
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content

def _analyze_with_together(batch_text):
    """Analyze batch using Together AI."""
    if not settings.TOGETHER_API_KEY:
        raise Exception("Together API Key missing")

    log.debug("Using Together AI for analysis...")
    client = OpenAI(api_key=settings.TOGETHER_API_KEY, base_url="https://api.together.xyz/v1")
    
    response = client.chat.completions.create(
        model=settings.TOGETHER_MODEL or "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content

def _analyze_with_cerebras(batch_text):
    """Analyze batch using Cerebras Inference."""
    if not settings.CEREBRAS_API_KEY:
        raise Exception("Cerebras API Key missing")

    log.debug("Using Cerebras for analysis...")
    client = OpenAI(api_key=settings.CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1")
    
    response = client.chat.completions.create(
        model=settings.CEREBRAS_MODEL or "llama3.1-8b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content

def _analyze_with_moonshot(batch_text):
    """Analyze batch using Moonshot AI (Kimi)."""
    if not settings.MOONSHOT_API_KEY:
        raise Exception("Moonshot API Key missing")

    log.debug("Using Moonshot AI for analysis...")
    client = OpenAI(api_key=settings.MOONSHOT_API_KEY, base_url="https://api.moonshot.cn/v1")
    
    response = client.chat.completions.create(
        model=settings.MOONSHOT_MODEL or "moonshot-v1-8k",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content

def _analyze_with_nvidia(batch_text):
    """Analyze batch using NVIDIA NIM."""
    if not settings.NVIDIA_API_KEY:
        raise Exception("NVIDIA API Key missing")

    log.debug("Using NVIDIA NIM for analysis...")
    client = OpenAI(api_key=settings.NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")
    
    response = client.chat.completions.create(
        model=settings.NVIDIA_MODEL or "meta/llama-3.1-70b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze these posts and return the source field exactly as given in each post header: {batch_text}"}
        ],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content

def _get_post_metadata(p):
    """Safely get metadata dict from a post (handles both dict and JSON string)."""
    meta = p.get('metadata', {})
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    return meta if isinstance(meta, dict) else {}

def _get_post_url(p):
    """Extract the best URL from a post."""
    meta = _get_post_metadata(p)
    return meta.get('url', '') or p.get('url', '')

def analyze_batch(posts):
    """Analyze a batch of posts using AI with proper per-post source attribution."""
    # Build a URL lookup map keyed by source so we can attribute correctly
    source_url_map = {}  # source -> first URL for that source in this batch
    all_source_urls = []

    for p in posts:
        url = _get_post_url(p)
        src = p.get('source', '')
        if url:
            if url not in all_source_urls:
                all_source_urls.append(url)
            if src not in source_url_map:
                source_url_map[src] = url

    # Build batch text with source embedded in each post header
    batch_text = "\n---\n".join([
        f"Source: {p['source']} | URL: {_get_post_url(p) or 'N/A'}\nContent: {p['content']}"
        for p in posts
    ])

    # Build provider fallback order based on PRIMARY_AI setting
    primary = settings.PRIMARY_AI or "groq"
    all_providers = ["groq", "together", "cerebras", "moonshot", "nvidia", "gemini", "anthropic"]
    # Put primary first, then the rest
    order = [primary] + [p for p in all_providers if p != primary]

    last_error = ""
    for ai_provider in order:
        try:
            log.info(f"Using {ai_provider} for analysis...")
            if ai_provider == "anthropic":
                raw_response = _analyze_with_anthropic(batch_text)
            elif ai_provider == "gemini":
                raw_response = _analyze_with_gemini(batch_text)
            elif ai_provider == "groq":
                raw_response = _analyze_with_groq(batch_text)
            elif ai_provider == "together":
                raw_response = _analyze_with_together(batch_text)
            elif ai_provider == "cerebras":
                raw_response = _analyze_with_cerebras(batch_text)
            elif ai_provider == "moonshot":
                raw_response = _analyze_with_moonshot(batch_text)
            elif ai_provider == "nvidia":
                raw_response = _analyze_with_nvidia(batch_text)
            else:
                continue

            # Clean response (strip markdown)
            raw_response = raw_response.strip()
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0].strip()

            ideas = json.loads(raw_response)

            # FIX: Assign correct source + real URL per idea (not just first post in batch)
            for i in ideas:
                # Use source returned by AI, fall back to first post's source
                idea_source = i.get("source") or posts[0]["source"]
                # Validate it's a known source name
                known_sources = {'reddit', 'hn', 'twitter', 'ih', 'producthunt', 'trends', 'playstore', 'custom'}
                if idea_source not in known_sources:
                    idea_source = posts[0]["source"]

                # Get the real URL for this source
                idea_source_url = source_url_map.get(idea_source, all_source_urls[0] if all_source_urls else '')

                i["source"] = idea_source
                i["source_url"] = idea_source_url
                i["source_urls"] = all_source_urls
                i["source_ref"] = idea_source_url

                # Calculate overall score from component scores
                demand = i.get("score_demand", 50)
                comp = i.get("score_competition", 50)
                trend = i.get("score_trend", 50)
                unique = i.get("uniqueness", i.get("score_uniqueness", 50))
                i["score_uniqueness"] = unique
                i["score_overall"] = round((demand * 0.4 + (100 - comp) * 0.3 + trend * 0.2 + unique * 0.1) / 10, 1)

            log.info(f"Successfully extracted {len(ideas)} ideas using {ai_provider}")
            return ideas

        except Exception as e:
            log.warning(f"{ai_provider} failed: {e}")
            last_error = str(e)
            continue

    raise Exception(f"All AI providers failed. Last error: {last_error}")

def run_analysis(posts, batch_size=25):
    """Run AI analysis on all posts with rate-limiting for free-tier APIs.
    
    Free tier limits (Gemini):
    - 15 requests per minute
    - 1500 requests per day
    
    We use batch_size=25 to minimize API calls (20 batches for 500 posts instead of 50).
    We add a 25-second delay between calls to stay well under the 15 RPM limit.
    """
    import time
    
    log.info(f"Starting AI analysis for {len(posts)} posts (batch size: {batch_size})...")

    all_ideas = []
    total_batches = (len(posts) + batch_size - 1) // batch_size
    consecutive_failures = 0
    max_consecutive_failures = 3  # Stop after 3 rate-limit errors in a row

    for i in range(0, len(posts), batch_size):
        batch_num = i // batch_size + 1
        batch = posts[i:i+batch_size]

        try:
            log.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} posts)...")
            ideas = analyze_batch(batch)
            all_ideas.extend(ideas)
            log.info(f"Batch {batch_num} complete: {len(ideas)} ideas extracted")
            consecutive_failures = 0  # Reset on success
            
            # Rate-limit delay: wait between successful calls to avoid hitting limits
            if batch_num < total_batches:
                delay = 25  # 25 seconds = ~2.4 requests/minute, well under 15 RPM limit
                log.info(f"Waiting {delay}s before next batch (rate-limit protection)...")
                time.sleep(delay)

        except Exception as e:
            error_msg = str(e)
            consecutive_failures += 1
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                log.warning(f"Batch {batch_num} rate-limited. Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                
                if consecutive_failures >= max_consecutive_failures:
                    log.error(f"Stopping analysis: {consecutive_failures} consecutive rate-limit errors. "
                             f"Successfully processed {len(all_ideas)} ideas from {batch_num - consecutive_failures} batches. "
                             f"Wait a few minutes and run again to process remaining posts.")
                    break
                
                # Wait longer after a rate-limit error
                wait_time = 65  # Wait just over a minute for rate limit reset
                log.info(f"Rate limited — waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                log.error(f"Batch {batch_num} failed: {e}")
                if consecutive_failures >= max_consecutive_failures:
                    log.error(f"Stopping: {consecutive_failures} consecutive non-rate-limit failures.")
                    break
                continue

    log.info(f"AI analysis complete: {len(all_ideas)} total ideas extracted from {len(posts)} posts")
    return all_ideas


def generate_launch_plan(idea):
    """Generate an A-Z Launch Plan for an idea."""
    log.debug(f"Generating A-Z Launch Plan for idea: {idea.get('name', 'Unknown')}")

    source_ref = idea.get('source_url') or idea.get('source_ref', 'N/A')
    prompt = f"""You are a top-tier Startup Founder & Marketing Expert.
Generate a comprehensive 'A-Z Launch Plan' for this validated startup idea:
Name: {idea['name']}
Description: {idea['description']}
Pain Point: {idea['pain_point']}
Keywords: {', '.join(idea.get('keywords', []) if isinstance(idea.get('keywords'), list) else [])}
Original Source: {source_ref}

Your output MUST be a highly structured Markdown document with the following sections:
1. **Executive Summary**: 2 sentences on why this will work.
2. **Competitor Analysis**: Identify 3 existing alternatives and how we differentiate.
3. **SEO & Content Strategy**: Give a page title, meta description, H1, and 3 content marketing ideas.
4. **30-Day Playbook**:
   - Days 1-7: MVP Build & Foundation
   - Days 8-14: Alpha Testing & Iteration
   - Days 15-21: Waitlist & Pre-launch Marketing
   - Days 22-30: Official Launch (Product Hunt, Reddit, etc.)
5. **Growth Hacks**: 3 specific strategies to get the first 100 users.

Output in clean, professional Markdown."""

    primary = settings.PRIMARY_AI or "groq"
    all_providers = ["groq", "together", "cerebras", "moonshot", "nvidia", "gemini", "anthropic"]
    order = [primary] + [p for p in all_providers if p != primary]
    for ai in order:
        try:
            if ai == "gemini":
                return _analyze_with_gemini(prompt)
            elif ai == "anthropic":
                return _analyze_with_anthropic(prompt)
            elif ai == "groq":
                return _analyze_with_groq(prompt)
            elif ai == "together":
                return _analyze_with_together(prompt)
            elif ai == "cerebras":
                return _analyze_with_cerebras(prompt)
            elif ai == "moonshot":
                return _analyze_with_moonshot(prompt)
            elif ai == "nvidia":
                return _analyze_with_nvidia(prompt)
        except Exception as e:
            log.warning(f"Failed to generate A-Z Launch Plan using {ai}: {e}")
            continue

    return "Failed to generate A-Z Launch Plan."
