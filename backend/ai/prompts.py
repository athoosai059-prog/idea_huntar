"""
Structured prompts for all deep analysis research types.
Each prompt is designed to produce industry-standard, actionable output.
"""


def competitor_analysis_prompt(idea: dict) -> str:
    """Generate a prompt for deep competitor analysis."""
    keywords = idea.get('keywords', [])
    if isinstance(keywords, str):
        import json
        try:
            keywords = json.loads(keywords)
        except Exception:
            keywords = []

    return f"""You are a senior market intelligence analyst. Conduct a thorough competitive analysis for this startup idea:

**Idea Name:** {idea.get('name', 'N/A')}
**Description:** {idea.get('description', 'N/A')}
**Pain Point:** {idea.get('pain_point', 'N/A')}
**Target Keywords:** {', '.join(keywords) if keywords else 'N/A'}
**Market Evidence:** {idea.get('market_evidence', 'N/A')}

Produce a detailed analysis in clean Markdown with these EXACT sections:

## 1. Direct Competitors (5-7 companies)
For EACH competitor list:
- **Company Name** + Website URL
- What they do (1 sentence)
- Pricing model (free tier / freemium / paid — with actual price ranges if known)
- Key strengths (2-3 bullet points)
- Key weaknesses or negative user feedback (2-3 bullet points)
- Estimated market share or user base (order of magnitude)

## 2. Indirect Competitors & Substitutes
- What workarounds are people using today? (spreadsheets, manual processes, etc.)
- Adjacent tools that partially solve this problem

## 3. Feature Comparison Matrix
Create a Markdown table comparing the top 5 competitors across 8-10 key features. Use ✅ / ❌ / ⚠️ (partial).

## 4. Pricing Landscape
- What is the typical price range in this market?
- Is there room for a freemium model?
- What pricing strategy would give the best competitive advantage?

## 5. Market Gaps & Opportunities
- What are competitors NOT doing that users want?
- Where are the 1-star reviews and complaints focused?
- What integration or feature gap creates the biggest opportunity?

## 6. Competitive Positioning Recommendation
- Recommended positioning statement (1 sentence)
- Key differentiators to emphasize (3 bullets)
- "Don't compete on" list — areas to deliberately avoid

Be specific. Use real company names where possible. No generic advice."""


def seo_strategy_prompt(idea: dict) -> str:
    """Generate a prompt for comprehensive SEO strategy."""
    keywords = idea.get('keywords', [])
    if isinstance(keywords, str):
        import json
        try:
            keywords = json.loads(keywords)
        except Exception:
            keywords = []

    return f"""You are a senior SEO strategist with 10+ years of experience ranking SaaS products on Google. Create a complete, actionable SEO strategy for this product:

**Product Name:** {idea.get('name', 'N/A')}
**Description:** {idea.get('description', 'N/A')}
**Pain Point Solved:** {idea.get('pain_point', 'N/A')}
**Seed Keywords:** {', '.join(keywords) if keywords else 'N/A'}

Produce a detailed strategy in clean Markdown with these EXACT sections:

## 1. Keyword Research
### Primary Keywords (5 high-intent)
For each: keyword, estimated search intent (informational/commercial/transactional), estimated difficulty (low/medium/high)

### Long-Tail Keywords (15 keywords)
Group into clusters by topic. These should be realistic, specific phrases people actually search.

### Question Keywords (5 "People Also Ask")
Format: question + recommended content type to answer it

## 2. On-Page SEO Blueprint
- **Homepage Title Tag** (under 60 chars)
- **Homepage Meta Description** (under 155 chars)
- **URL Structure** recommendation
- **H1 → H2 → H3 Hierarchy** for the landing page
- **Internal Linking Strategy** (hub & spoke model)

## 3. Content Strategy (3-Month Calendar)
Create a table with 12 content pieces (1/week for 12 weeks):
| Week | Title | Target Keyword | Content Type | Funnel Stage |
Include a mix of: comparison posts, how-to guides, listicles, case studies

## 4. Technical SEO Checklist
- Schema markup recommendations (specific schema types with examples)
- Core Web Vitals targets
- Sitemap & robots.txt guidance
- Mobile optimization priorities
- Page speed requirements

## 5. Link Building Strategy
- 5 specific link building tactics ranked by effort vs. impact
- Target domains/publications to pitch
- Content formats that naturally attract backlinks

## 6. Local/Niche SEO (if applicable)
- Directory submissions
- Community engagement strategy (Reddit, forums, Slack groups)
- Social signals strategy

## 7. Measurement & KPIs
- Month 1 targets (baseline)
- Month 3 targets (traction)
- Month 6 targets (growth)
- Key metrics to track weekly

Be specific and actionable. Every recommendation should be something a developer or marketer can execute THIS WEEK."""


def consensus_launch_plan_prompt(idea: dict) -> str:
    """Generate a prompt for industry-standard A-Z launch plan."""
    keywords = idea.get('keywords', [])
    if isinstance(keywords, str):
        import json
        try:
            keywords = json.loads(keywords)
        except Exception:
            keywords = []

    features = idea.get('potential_features', [])
    if isinstance(features, str):
        import json
        try:
            features = json.loads(features)
        except Exception:
            features = []

    return f"""You are a Y Combinator-caliber startup advisor. Create an industry-standard, execution-ready launch plan for this validated startup idea:

**Idea Name:** {idea.get('name', 'N/A')}
**Description:** {idea.get('description', 'N/A')}
**Detailed Description:** {idea.get('detailed_description', 'N/A')}
**Pain Point:** {idea.get('pain_point', 'N/A')}
**Market Evidence:** {idea.get('market_evidence', 'N/A')}
**Potential Features:** {', '.join(features) if features else 'N/A'}
**Keywords:** {', '.join(keywords) if keywords else 'N/A'}

Produce a comprehensive, phase-by-phase launch plan in clean Markdown:

## Phase 0: Validation (Week 1) — Before Writing Code
- Problem validation: 5 specific questions to ask potential users
- Landing page structure (hero, pain point, solution, CTA)
- Waitlist/email capture tool recommendation
- Smoke test ads: 3 ad copy variations + $50 budget allocation
- Success criteria: what numbers prove the idea is worth building?

## Phase 1: MVP Build (Weeks 2-4)
- **Core Feature Set**: The 3-5 features for v1.0 (nothing more)
- **Recommended Tech Stack** with reasoning (frontend, backend, database, hosting)
- **Database Schema**: Key tables/collections needed
- **API Design**: List the 5-10 most important endpoints
- **CI/CD Pipeline**: Recommended setup
- **Estimated Build Time**: For a solo developer vs. 2-person team

## Phase 2: Beta Testing (Weeks 5-6)
- Beta user recruitment: 3 specific channels to find first 20 users
- Feedback collection: What tool to use + what questions to ask
- Bug tracking & prioritization framework
- Key metrics to track: DAU, retention rate, NPS score targets

## Phase 3: Launch (Weeks 7-8)
- **Product Hunt Launch Checklist** (day-by-day for launch week)
- **Reddit/HackerNews Strategy**: Which subreddits, posting format, timing
- **Press & Media**: 3 angles for tech press pitches
- **Social Media Launch Sequence**: Day-by-day posting schedule
- **Email Sequence**: 3 emails to waitlist (announce → tutorial → social proof)

## Phase 4: Growth (Weeks 9-12)
- Content marketing: 4 specific blog post topics that will rank
- SEO quick wins: 3 things to implement immediately
- Paid acquisition: Recommended channels + starting daily budget
- Partnership opportunities: 3 types of companies to partner with
- Community building: Where to create a user community

## Phase 5: Monetization & Scale (Month 3+)
- **Pricing Strategy**: Specific pricing tiers with features per tier
- **Revenue Projections**: Conservative Month 1-6 estimates
- **Unit Economics**: Target CAC, LTV, and payback period
- **When to Hire**: What role to hire first and at what MRR milestone

## Risk Assessment
- Top 3 risks to the business + mitigation strategy for each
- Competitive moat: How to build defensibility over time

Every recommendation must be SPECIFIC and ACTIONABLE — no generic advice like "build a great product". Include tool names, price ranges, and concrete numbers."""


def consensus_synthesis_prompt(individual_plans: dict, idea_name: str, analysis_type: str) -> str:
    """Generate the meta-prompt to synthesize multiple AI responses into a consensus."""

    plans_text = ""
    for provider, content in individual_plans.items():
        plans_text += f"\n\n---\n## Analysis from {provider.upper()}\n---\n{content}\n"

    n = len(individual_plans)

    type_labels = {
        "consensus_plan": "A-Z Launch Plan",
        "competitor_analysis": "Competitor Analysis",
        "seo_strategy": "SEO Strategy",
    }
    label = type_labels.get(analysis_type, analysis_type)

    return f"""You are a senior strategy consultant synthesizing {n} independent {label} analyses for the startup idea: **{idea_name}**.

Below are {n} plans generated independently by different AI systems. They did NOT see each other's work.

{plans_text}

---

## YOUR TASK: Synthesize a Final Consensus {label}

Follow these rules strictly:

### 1. 🟢 HIGH CONFIDENCE (2+ AIs agree)
Extract every recommendation, insight, or data point that at least 2 out of {n} AIs independently mentioned. Present these as the primary recommendations. These are validated.

### 2. 🔵 INDUSTRY STANDARD (3+ AIs agree)
If 3 or more AIs agree on a specific recommendation, mark it with a 🔵 badge. These represent industry-standard best practices.

### 3. 🟡 UNIQUE INSIGHT (1 AI only)
Note any standout recommendation from a single AI that others missed. These could be innovative or niche — flag them for the user to evaluate.

### 4. 🔴 DISAGREEMENT
Where AIs gave contradictory advice, present both sides and explain the trade-off. Let the user decide.

### Format
- Use the same section structure as the individual plans
- Start each section with a confidence summary: "X/{n} AIs agree on this approach"
- Be comprehensive — don't drop good recommendations just because only 1 AI mentioned them
- At the end, add a "Consensus Score" section showing overall agreement percentage

Output in clean, professional Markdown."""
