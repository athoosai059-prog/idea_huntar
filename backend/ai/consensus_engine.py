"""
Multi-AI Consensus Engine.
Runs the same prompt across ALL configured AI providers independently,
then synthesizes a final plan from points where multiple AIs agree.
"""

import json
import concurrent.futures
import time
from backend.config import settings
from backend.utils.logging_config import get_logger
from backend.ai.prompts import (
    competitor_analysis_prompt,
    seo_strategy_prompt,
    consensus_launch_plan_prompt,
    consensus_synthesis_prompt,
)

log = get_logger(__name__)


# ── Provider execution helpers ──────────────────────────────────────

def _call_provider(provider_name: str, prompt: str) -> str | None:
    """Call a single AI provider and return its response text, or None on failure."""
    from openai import OpenAI
    try:
        if provider_name == "groq":
            if not settings.GROQ_API_KEY:
                return None
            import groq
            client = groq.Groq(api_key=settings.GROQ_API_KEY)
            r = client.chat.completions.create(
                model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096, temperature=0.3,
            )
            return r.choices[0].message.content

        elif provider_name == "together":
            if not settings.TOGETHER_API_KEY:
                return None
            client = OpenAI(api_key=settings.TOGETHER_API_KEY, base_url="https://api.together.xyz/v1")
            r = client.chat.completions.create(
                model=settings.TOGETHER_MODEL or "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096, temperature=0.3,
            )
            return r.choices[0].message.content

        elif provider_name == "cerebras":
            if not settings.CEREBRAS_API_KEY:
                return None
            client = OpenAI(api_key=settings.CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1")
            r = client.chat.completions.create(
                model=settings.CEREBRAS_MODEL or "llama3.1-8b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096, temperature=0.3,
            )
            return r.choices[0].message.content

        elif provider_name == "moonshot":
            if not settings.MOONSHOT_API_KEY:
                return None
            client = OpenAI(api_key=settings.MOONSHOT_API_KEY, base_url="https://api.moonshot.cn/v1")
            r = client.chat.completions.create(
                model=settings.MOONSHOT_MODEL or "moonshot-v1-8k",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return r.choices[0].message.content

        elif provider_name == "nvidia":
            if not settings.NVIDIA_API_KEY:
                return None
            client = OpenAI(api_key=settings.NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")
            r = client.chat.completions.create(
                model=settings.NVIDIA_MODEL or "meta/llama-3.1-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096, temperature=0.3,
            )
            return r.choices[0].message.content

        elif provider_name == "gemini":
            if not settings.GEMINI_API_KEY:
                return None
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(max_output_tokens=4096),
            )
            return response.text

        elif provider_name == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                return None
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            message = client.messages.create(
                model=settings.CLAUDE_MODEL or "claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        return None

    except Exception as e:
        log.warning(f"Provider {provider_name} failed: {e}")
        return None


# ── Core consensus logic ────────────────────────────────────────────

ALL_PROVIDERS = ["groq", "together", "cerebras", "moonshot", "nvidia", "gemini", "anthropic"]


def _get_available_providers() -> list[str]:
    """Return list of providers that have API keys configured."""
    key_map = {
        "groq": settings.GROQ_API_KEY,
        "together": settings.TOGETHER_API_KEY,
        "cerebras": settings.CEREBRAS_API_KEY,
        "moonshot": settings.MOONSHOT_API_KEY,
        "nvidia": settings.NVIDIA_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
    }
    available = [name for name, key in key_map.items() if key]
    log.info(f"Available AI providers for consensus: {available}")
    return available


def _build_prompt(idea: dict, analysis_type: str) -> str:
    """Build the appropriate prompt for the given analysis type."""
    if analysis_type == "competitor_analysis":
        return competitor_analysis_prompt(idea)
    elif analysis_type == "seo_strategy":
        return seo_strategy_prompt(idea)
    elif analysis_type == "consensus_plan":
        return consensus_launch_plan_prompt(idea)
    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")


def run_consensus(idea: dict, analysis_type: str) -> dict:
    """
    Run the same prompt across ALL available AI providers, then synthesize.

    Returns:
        {
            "consensus": str,           # The synthesized plan
            "individual_plans": {        # Each provider's raw response
                "groq": str,
                "gemini": str,
                ...
            },
            "providers_used": int,       # How many providers succeeded
            "providers_total": int,      # How many were attempted
            "confidence": float,         # 0.0 - 1.0 based on agreement
        }
    """
    prompt = _build_prompt(idea, analysis_type)
    available = _get_available_providers()

    if len(available) == 0:
        raise Exception("No AI providers configured. Please add at least one API key in Settings.")

    log.info(f"Running consensus {analysis_type} across {len(available)} providers: {available}")

    # ── Step 1: Fire all providers in parallel ────────────────────
    individual_plans = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(available)) as executor:
            future_to_provider = {
                executor.submit(_call_provider, provider, prompt): provider
                for provider in available
            }
            for future in concurrent.futures.as_completed(future_to_provider, timeout=180):
                provider = future_to_provider[future]
                try:
                    result = future.result(timeout=60)
                    if result and len(result.strip()) > 100:
                        individual_plans[provider] = result
                        log.info(f"✅ {provider} returned {len(result)} chars")
                    else:
                        log.warning(f"❌ {provider} returned empty/too-short response")
                except Exception as e:
                    log.warning(f"❌ {provider} raised exception: {e}")
    except concurrent.futures.TimeoutError:
        log.warning(f"Consensus timed out. Got {len(individual_plans)} results before timeout.")
    except Exception as e:
        log.error(f"Thread pool error: {e}")

    providers_used = len(individual_plans)
    log.info(f"Consensus: {providers_used}/{len(available)} providers returned results")

    if providers_used == 0:
        return {
            "consensus": "All AI providers failed. Check your API keys and quotas, then try again.",
            "individual_plans": {},
            "providers_used": 0,
            "providers_total": len(available),
            "confidence": 0.0,
        }

    # ── Step 2: If only 1 provider, return it directly (no synthesis) ─
    if providers_used == 1:
        solo_provider = list(individual_plans.keys())[0]
        solo_plan = list(individual_plans.values())[0]
        return {
            "consensus": f"*Generated by {solo_provider} (only 1 provider available — no consensus possible)*\n\n{solo_plan}",
            "individual_plans": individual_plans,
            "providers_used": 1,
            "providers_total": len(available),
            "confidence": 0.5,
        }

    # ── Step 3: Synthesize consensus using the primary AI ─────────
    # Truncate individual plans if too long to prevent token overflow
    truncated_plans = {}
    MAX_PLAN_CHARS = 4000  # ~1000 tokens per plan
    for provider, plan in individual_plans.items():
        if len(plan) > MAX_PLAN_CHARS:
            truncated_plans[provider] = plan[:MAX_PLAN_CHARS] + "\n\n[... truncated for synthesis ...]"
        else:
            truncated_plans[provider] = plan

    synthesis_prompt = consensus_synthesis_prompt(
        truncated_plans,
        idea.get("name", "Unknown"),
        analysis_type,
    )

    # Use primary AI for synthesis, with fallback
    primary = settings.PRIMARY_AI or "groq"
    synthesis_order = [primary] + [p for p in ALL_PROVIDERS if p != primary]

    consensus_text = None
    for synth_provider in synthesis_order:
        try:
            log.info(f"Synthesizing consensus using {synth_provider}...")
            consensus_text = _call_provider(synth_provider, synthesis_prompt)
            if consensus_text and len(consensus_text.strip()) > 100:
                log.info(f"✅ Consensus synthesized by {synth_provider} ({len(consensus_text)} chars)")
                break
            else:
                consensus_text = None
        except Exception as e:
            log.warning(f"Synthesis with {synth_provider} failed: {e}")
            continue

    # Fallback: if synthesis fails, just concatenate all plans
    if not consensus_text:
        log.warning("Synthesis failed with all providers. Returning concatenated plans.")
        parts = []
        for provider, plan in individual_plans.items():
            parts.append(f"## Plan from {provider.upper()}\n\n{plan}")
        consensus_text = "# Combined Plans (synthesis unavailable)\n\n" + "\n\n---\n\n".join(parts)

    confidence = min(1.0, providers_used / max(len(available), 1))

    return {
        "consensus": consensus_text,
        "individual_plans": individual_plans,
        "providers_used": providers_used,
        "providers_total": len(available),
        "confidence": round(confidence, 2),
    }


# ── Convenience functions ───────────────────────────────────────────

def run_competitor_analysis(idea: dict) -> dict:
    """Run multi-AI consensus competitor analysis."""
    return run_consensus(idea, "competitor_analysis")


def run_seo_strategy(idea: dict) -> dict:
    """Run multi-AI consensus SEO strategy."""
    return run_consensus(idea, "seo_strategy")


def run_consensus_launch_plan(idea: dict) -> dict:
    """Run multi-AI consensus A-Z launch plan."""
    return run_consensus(idea, "consensus_plan")
