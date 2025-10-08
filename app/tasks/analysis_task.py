from celery import Task
from loguru import logger
from app.celery import app

from app.llm.utils import openai_client, tavily_client
import json
import asyncio


class CallbackTask(Task):
    """Base task with progress callback support"""

    def update_progress(self, state: str, meta: dict):
        """Update task state with progress information"""
        self.update_state(state=state, meta=meta)


async def call_research_plan(query: str, user_context: dict = None):
    """Decompose financial query into structured research sub-questions"""
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


async def call_resource_search(query: str, context: str = None):
    """Internet search for financial data, research, and market intelligence"""
    search_params = {
        "query": query,
        "include_raw_content": "markdown",
        "max_results": 5,
    }

    if any(
        term in query.lower()
        for term in ["recent", "latest", "current", "2024", "2025"]
    ):
        search_params["days"] = 30

    res = await tavily_client.search(**search_params)
    search_results = res.get("results", [])

    logger.info(
        f"Successfully retrieved {len(search_results)} financial search results"
    )

    processed_results = []
    for idx, result in enumerate(search_results[:8], 1):
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


async def call_generate_analysis(
    research_plan: str,
    search_results: list,
    reasoning_depth: str = "standard",
):
    """Synthesize research findings into structured financial analysis"""
    # Simplified version for Celery task
    SYSTEM_PROMPT = """
        You are a financial analyst who synthesizes research into clear, actionable insights.

        Build a logical analysis by connecting research findings into causal chains and scenario models.
        Provide executive summary, key findings, scenario analysis, and actionable implications.
        """

    search_summary = "\n\n".join(
        [f"**Source {i + 1}**: {result}" for i, result in enumerate(search_results)]
    )

    res = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Synthesize these research findings:
                    
                    **Research Plan**:
                    {research_plan}
                    
                    **Search Results**:
                    {search_summary}
                    
                    Reasoning depth: {reasoning_depth}
                    """,
            },
        ],
    )

    return res.choices[0].message.content


async def call_self_reflection(analysis: str, quality_threshold: float = 8.0):
    """Validate analysis quality and identify gaps"""
    SYSTEM_PROMPT = """
        You are a quality assurance analyst validating financial research.

        Audit the analysis for gaps, contradictions, and quality issues. Suggest improvements.
        Provide overall quality score and recommendations.
        """

    res = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
                    Validate this financial analysis:
                    {analysis}
                    
                    Quality threshold: {quality_threshold}/10
                    """,
            },
        ],
    )
    return res.choices[0].message.content


async def financial_analysis(
    task_instance,
    query: str,
    user_context: dict = None,
    reasoning_depth: str = "standard",
) -> dict:
    """
    Internal async implementation of financial analysis workflow

    Args:
        task_instance: The Celery task instance for progress updates
        query: The financial question to analyze
        user_context: Optional user context (portfolio, risk tolerance, etc.)
        reasoning_depth: How deep to go with analysis

    Returns:
        dict: Complete analysis results with all phases
    """
    try:
        self = task_instance
        result = {
            "query": query,
            "phases": {},
            "status": "processing",
        }

        # Phase 1: Research Planning
        logger.info(f"Task {self.request.id}: Starting research planning")
        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "planning",
                "status": "started",
                "message": "📋 Decomposing financial query into research dimensions...",
                "progress": 10,
            },
        )

        plan = await call_research_plan(query, user_context)
        if not plan:
            raise ValueError("Failed to generate research plan")
        result["phases"]["planning"] = plan

        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "planning",
                "status": "completed",
                "message": "✅ Research plan created",
                "progress": 25,
                "result": plan,
            },
        )

        # Phase 2: Resource Search (Multiple searches)
        logger.info(f"Task {self.request.id}: Starting resource search")
        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "research",
                "status": "started",
                "message": "🔍 Gathering market data, news, and expert analysis...",
                "progress": 30,
            },
        )

        # Extract search queries from plan (simplified - adjust based on your plan structure)
        search_results = []
        search_queries = [
            query,  # Main query
            f"{query} market analysis",
            f"{query} expert opinion",
        ]

        for idx, search_query in enumerate(search_queries):
            logger.info(f"Task {self.request.id}: Searching - {search_query}")
            search_result = await call_resource_search(
                search_query, context=f"Research for: {query}"
            )
            search_results.append(search_result)

            progress = 30 + (idx + 1) * 10  # 30, 40, 50
            self.update_progress(
                state="PROGRESS",
                meta={
                    "phase": "research",
                    "status": "in_progress",
                    "message": f"🔍 Completed search {idx + 1}/{len(search_queries)}",
                    "progress": progress,
                    "searches_completed": idx + 1,
                    "total_searches": len(search_queries),
                },
            )

        result["phases"]["research"] = search_results

        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "research",
                "status": "completed",
                "message": "✅ Research completed",
                "progress": 60,
            },
        )

        # Phase 3: Generate Analysis
        logger.info(f"Task {self.request.id}: Generating analysis")
        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "analysis",
                "status": "started",
                "message": "🎯 Synthesizing findings into causal logic and scenarios...",
                "progress": 65,
            },
        )

        analysis_result = await call_generate_analysis(
            research_plan=plan or "",
            search_results=search_results,
            reasoning_depth=reasoning_depth,
        )
        if not analysis_result:
            raise ValueError("Failed to generate analysis")
        result["phases"]["analysis"] = analysis_result

        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "analysis",
                "status": "completed",
                "message": "✅ Analysis generated",
                "progress": 85,
            },
        )

        # Phase 4: Self-Reflection
        logger.info(f"Task {self.request.id}: Running self-reflection")
        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "validation",
                "status": "started",
                "message": "🔧 Auditing analysis quality and logical consistency...",
                "progress": 90,
            },
        )

        reflection = await call_self_reflection(
            analysis_result or "",
        )
        result["phases"]["validation"] = reflection

        self.update_progress(
            state="PROGRESS",
            meta={
                "phase": "validation",
                "status": "completed",
                "message": "✅ Quality validation complete",
                "progress": 95,
            },
        )

        # Mark as complete
        result["status"] = "completed"
        logger.info(f"Task {self.request.id}: Analysis completed successfully")

        return result

    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {str(e)}")
        self.update_progress(
            state="FAILURE",
            meta={
                "phase": "error",
                "status": "failed",
                "message": f"❌ Analysis failed: {str(e)}",
                "error": str(e),
            },
        )
        raise


@app.task(
    bind=True,
    base=CallbackTask,
    name="app.tasks.analysis_task.financial_analysis",
    track_started=True,
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
def financial_analysis_task(
    self,
    query: str,
    user_context: dict = None,
    reasoning_depth: str = "standard",
) -> dict:
    """
    Complete financial analysis workflow as a Celery task

    This is a synchronous wrapper that runs the async implementation using asyncio.run()
    to ensure proper async handling within Celery.

    Args:
        query: The financial question to analyze
        user_context: Optional user context (portfolio, risk tolerance, etc.)
        reasoning_depth: How deep to go with analysis

    Returns:
        dict: Complete analysis results with all phases
    """
    return asyncio.run(financial_analysis(self, query, user_context, reasoning_depth))
