import json
from agents import function_tool
from loguru import logger
from app.llm.utils import openai_client, tavily_client


@function_tool()
async def research_plan(query: str, user_context: dict = None) -> str | None:
    """
    Decompose financial query into structured research sub-questions

    Args:
        query (str): The financial question or analysis request to plan research for
        user_context (dict, optional): Optional user context (portfolio, time horizon, risk tolerance)

    Returns:
        str: The research plan
    """

    SYSTEM_PROMPT = """
        You are a financial research strategist who breaks down complex market questions into investigable components.

        # YOUR TASK
        Transform any financial query into a structured research blueprint with clear sub-questions and data requirements.

        # OUTPUT FORMAT

        **Primary Question**: [Restate the main query clearly]

        **Research Dimensions**:

        1. **[Dimension Name]** (Priority: High/Medium/Low)
        - Sub-question: [Specific question to investigate]
        - Data needed: [Market data/News/Research/On-chain metrics]
        - Why it matters: [Brief relevance explanation]

        2. **[Dimension Name]** (Priority: High/Medium/Low)
        - Sub-question: [Specific question to investigate]
        - Data needed: [Required data types]
        - Why it matters: [Brief relevance explanation]

        [Continue for 4-6 dimensions...]

        **Research Strategy**:
        - Parallel searches: [Which dimensions can be researched simultaneously]
        - Sequential dependencies: [What must be answered before what]
        - Time horizon: [Historical lookback + forecast period]

        **Key Assumptions to Track**:
        - [Assumption 1]
        - [Assumption 2]
        - [Assumption 3]

        # PRINCIPLES
        - Break complex queries into specific, answerable sub-questions
        - Identify what data sources are needed for each dimension
        - Flag dependencies between sub-questions
        - Keep it focused: 4-6 dimensions maximum
        """

    context_str = ""
    if user_context:
        context_str = f"""
            User Context:
            - Portfolio: {user_context.get("portfolio", "Not specified")}
            - Time horizon: {user_context.get("time_horizon", "Not specified")}
            - Risk tolerance: {user_context.get("risk_tolerance", "Not specified")}
        """

    res = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Create a research plan for this financial question:
                    {query}{context_str}
                    """,
            },
        ],
    )
    return res.choices[0].message.content


@function_tool()
async def resource_search(query: str, context: str = None) -> str | None:
    """
    Internet search for financial data, research, and market intelligence

    Args:
        query (str): The search query optimized for finding financial information (be specific, include dates if relevant)
        context (str, optional): Optional context about what research dimension this search supports

    Returns:
        str: The financial search results
    """

    # Execute Tavily search with financial context
    search_params = {
        "query": query,
        "include_raw_content": "markdown",
        "max_results": 5,
    }

    # Add date filtering for time-sensitive queries
    if any(
        term in query.lower()
        for term in ["recent", "latest", "current", "2024", "2025"]
    ):
        search_params["days"] = 30  # Last 30 days for recent queries

    res = await tavily_client.search(**search_params)
    search_results = res.get("results", [])

    logger.info(
        f"Successfully retrieved {len(search_results)} financial search results"
    )

    # Pre-process search results to reduce token count
    processed_results = []
    for idx, result in enumerate(search_results[:8], 1):  # Limit to top 8 results
        # Truncate raw_content to first 1500 characters if it exists
        raw_content = result.get("raw_content") or result.get("content") or ""
        truncated_content = (
            raw_content[:1500] + "..." if len(raw_content) > 1500 else raw_content
        )

        processed_results.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": truncated_content,
                "score": result.get("score", 0),
            }
        )

    logger.info("Processed and truncated search results for analysis")

    SYSTEM_PROMPT = """
        You are a financial intelligence analyst extracting key insights from web sources.

        # TASK
        Extract critical financial information and organize it for investment analysis.

        # EXTRACT
        - Market data: prices, volumes, metrics
        - Policy info: regulations, government actions
        - Expert opinions and forecasts
        - Historical context and precedents
        - Quantitative claims with dates
        - Contradicting views

        # OUTPUT FORMAT

        ## Key Findings
        ### [Insight Headline]
        - **Claim**: [Specific fact/data]
        - **Source**: [Publication] | [Date]
        - **Type**: [Data/Opinion/Research/News]

        ## Market Data
        - [Metric]: [Value] | [Date]

        ## Perspectives
        **Bullish**: [Claims with sources]
        **Bearish**: [Claims with sources]
        **Consensus**: [Common views]

        ## Quality
        - Tier 1 (Institutional): [count/list]
        - Tier 2 (Media/analysts): [count/list]

        # RULES
        - Cite all sources
        - Note dates explicitly
        - Include multiple perspectives
        - Flag opinion vs. data
        - Be concise but precise
        """

    context_str = f"\n\nContext: {context}" if context else ""

    res = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Query: {query}{context_str}

                    Search Results:
                    {json.dumps(processed_results, indent=2)}
                    """,
            },
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    logger.info("Successfully generated financial search results")
    return res.choices[0].message.content


@function_tool()
async def generate_analysis(
    research_plan: str,
    search_results: list,
    reasoning_depth: str = "standard",
    allow_checkpoints: bool = True,
) -> str | None:
    """
    Synthesize research findings into structured financial analysis with transparent reasoning

    Args:
        research_plan (str): The original research plan with sub-questions
        search_results (list): List of research findings from searches
        reasoning_depth (str, optional): How deep to go with causal chain analysis. Defaults to "standard".
        allow_checkpoints (bool, optional): Whether to include human-in-loop validation points. Defaults to True.

    Returns:
        str: The generated financial analysis
    """

    SYSTEM_PROMPT = """
        You are a financial analyst who synthesizes research into clear, actionable insights with transparent reasoning.

        # YOUR TASK
        Build a logical analysis by connecting research findings into causal chains and scenario models.

        # OUTPUT FORMAT

        ## Executive Summary
        [2-3 sentence bottom-line conclusion]

        ## Analytical Framework

        ### Finding 1: [Key Insight]
        **Evidence**: [What the data shows]
        **Source**: [Where this comes from]
        **Confidence**: [High/Medium/Low - with reasoning]

        **Causal Logic**:
        [Event/Condition] → [Mechanism] → [Market Impact]
        ↳ Supporting evidence: [Specific data points]
        ↳ Contradicting signals: [Alternative interpretations if any]

        ### Finding 2: [Key Insight]
        [Repeat structure...]

        ## Scenario Analysis

        **Base Case** (Probability: X%)
        - Scenario: [What happens in most likely path]
        - Market impact: [Specific price/direction expectations]
        - Key assumptions: [What needs to be true]
        - Invalidation signals: [What would prove this wrong]

        **Alternative Scenarios**
        [2-3 other plausible outcomes with probabilities]

        ## Actionable Implications
        - Positioning: [Specific recommendations]
        - Monitoring: [What metrics to watch]
        - Risk management: [Hedge considerations]
        - Rebalance triggers: [When to adjust]

        ## Confidence Assessment
        | Component | Confidence | Reasoning |
        |-----------|-----------|-----------|
        [Table showing confidence in each conclusion]

        ## Assumption Tracker
        ✓ [Assumption 1 - currently valid]
        ⚠ [Assumption 2 - monitor closely]
        ✗ [Assumption 3 - invalidated]

        ## Sources
        [Categorized list with links]

        # CHECKPOINT RULES (if allow_checkpoints=True)
        When reasoning has significant uncertainty or conflicting evidence:
        - Flag the ambiguity explicitly
        - Present both interpretations fairly
        - Ask: "Which framework seems more applicable given current conditions?"
        - Wait for user input before proceeding

        # PRINCIPLES
        - Show your reasoning work, don't just state conclusions
        - Quantify confidence levels with evidence
        - Flag contradictions rather than hiding them
        - Connect analysis to actionable decisions
        - Be precise about time horizons and magnitudes
        """

    search_summary = "\n\n".join(
        [f"**Source {i + 1}**: {result}" for i, result in enumerate(search_results)]
    )

    checkpoint_instruction = (
        "\n\nIMPORTANT: Include human checkpoints at points of high uncertainty."
        if allow_checkpoints
        else ""
    )

    res = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Synthesize these research findings into a structured analysis:
                    
                    **Research Plan**:
                    {research_plan}
                    
                    **Search Results**:
                    {search_summary}
                    
                    Reasoning depth: {reasoning_depth}{checkpoint_instruction}
                    """,
            },
        ],
    )

    return res.choices[0].message.content


@function_tool()
async def self_reflection(analysis: str, quality_threshold: float = 8.0) -> str | None:
    """
    Validate analysis quality and identify gaps before delivery

    Args:
        analysis (str): The generated financial analysis to validate
        quality_threshold (float, optional): Minimum quality score required (0-10 scale). Defaults to 8.0.

    Returns:
        str: The self-reflection report
    """

    SYSTEM_PROMPT = """
        You are a quality assurance analyst who validates financial research for completeness and logical consistency.

        # YOUR TASK
        Audit the analysis for gaps, contradictions, and quality issues. Suggest improvements.

        # VALIDATION CHECKLIST

        ## Completeness Audit
        - ✓/✗ All sub-questions addressed
        - ✓/✗ Sources cited for major claims
        - ✓/✗ Scenarios cover probability space (sum to ~100%)
        - ✓/✗ Actionable insights provided
        - ✓/✗ Assumptions explicitly stated

        ## Logical Consistency Check
        - Are there contradictions between different sections?
        - Do probability weights make sense?
        - Are time horizons consistent throughout?
        - Does scenario logic align with evidence?

        ## Source Quality Review
        - Tier 1 sources (Fed, BIS, top journals): [count]
        - Tier 2 sources (major media, established analysts): [count]  
        - Tier 3 sources (blogs, unverified): [count]
        - Data sources (APIs, databases): [count]
        - **Quality score**: [0-10]

        ## Confidence Calibration
        - Claims with 80%+ confidence: [count]
        → Do they have strong empirical support?
        - Claims with 40-60% confidence: [count]
        → Are uncertainties properly explained?
        - **Calibration assessment**: [Well-calibrated/Overconfident/Underconfident]

        ## Gap Analysis
        - Missing elements: [What's not covered that should be]
        - Weak areas: [Where analysis needs strengthening]
        - Expansion opportunities: [Optional deeper dives to offer]

        ## Bias Check
        - Recency bias: [Over-weighting recent events?]
        - Confirmation bias: [Did we seek disconfirming evidence?]
        - Anchoring: [Too tied to initial hypothesis?]

        # OUTPUT FORMAT

        **Overall Quality Score**: [0-10]

        **Strengths**:
        - [What's done well]

        **Recommendations**:
        1. [Specific action to improve quality]
        2. [Specific action to improve quality]

        **Deliver Analysis?**: [Yes / Refine first / Major revisions needed]

        # PRINCIPLES
        - Be specific about what's wrong and how to fix it
        - Prioritize issues by severity
        - Validate logic, not just check formatting
        - Ensure confidence levels match evidence strength
        """

    res = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Validate this financial analysis for quality and completeness:
                    {analysis}
                    
                    Quality threshold: {quality_threshold}/10
                    """,
            },
        ],
    )
    return res.choices[0].message.content
