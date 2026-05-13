"""
SEO Generator Pipeline — rewritten to use the multi-provider fallback chain.
"""
from backend.config import settings
from backend.ai.prompts import seo_strategy_prompt
from backend.utils.logging_config import get_logger

log = get_logger(__name__)


def generate_seo_brief(idea: dict) -> str:
    """
    Generate a complete SEO strategy for a specific idea.
    Uses the full provider fallback chain (same as analyzer.py).
    """
    from backend.ai.analyzer import (
        _analyze_with_groq,
        _analyze_with_together,
        _analyze_with_cerebras,
        _analyze_with_moonshot,
        _analyze_with_nvidia,
        _analyze_with_gemini,
        _analyze_with_anthropic,
    )

    log.info(f"Generating SEO Brief for idea: {idea.get('name', 'Unknown')}")
    prompt = seo_strategy_prompt(idea)

    primary = settings.PRIMARY_AI or "groq"
    all_providers = ["groq", "together", "cerebras", "moonshot", "nvidia", "gemini", "anthropic"]
    order = [primary] + [p for p in all_providers if p != primary]

    provider_funcs = {
        "groq": _analyze_with_groq,
        "together": _analyze_with_together,
        "cerebras": _analyze_with_cerebras,
        "moonshot": _analyze_with_moonshot,
        "nvidia": _analyze_with_nvidia,
        "gemini": _analyze_with_gemini,
        "anthropic": _analyze_with_anthropic,
    }

    for ai in order:
        try:
            func = provider_funcs.get(ai)
            if func:
                log.info(f"Trying {ai} for SEO Brief...")
                return func(prompt)
        except Exception as e:
            log.warning(f"SEO Brief generation failed with {ai}: {e}")
            continue

    return "Failed to generate SEO brief. Please check your API keys."
