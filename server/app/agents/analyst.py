"""
Analyst Agent for AquiferAI V2.0

Synthesizes query results into prescriptive, actionable insights and recommendations.

Key responsibilities:
1. Analyze data from successful queries
2. Extract meaningful patterns and insights
3. Generate prescriptive (not just descriptive) recommendations
4. Suggest follow-up questions
5. Provide visualization hints for the frontend

The analyst transforms raw data into business intelligence with a focus
on CO2 storage site selection and aquifer suitability assessment.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from app.graph.state import (
    AgentState,
    AnalysisReport,
    Insight,
    Recommendation,
    VisualizationHint,
    ValidationResult,
    ValidationStatus,
    ExecutionTraceStep
)
from app.core.llm_provider import get_llm_client, AgentName

logger = logging.getLogger(__name__)


ANALYST_SYSTEM_PROMPT = """You are the Analyst Agent for a CO2 storage site advisory system.

## Your Mission

Transform query results into **PRESCRIPTIVE ANALYTICS** - tell users what to DO, not just what IS.

## Domain Context: CO2 Storage in Saline Aquifers

### Why This Matters
- Power plants emit 3-5 megatonnes (Mt) CO2/year
- Saline aquifers can permanently store CO2 underground
- Site selection requires balancing capacity, risk, and technical feasibility

### Key Technical Parameters

**Porosity** (0-1 scale):
- >0.20 = Excellent (high storage potential)
- 0.15-0.20 = Good
- <0.15 = Poor (limited storage)

**Permeability** (millidarcies, md):
- >200 md = Excellent (easy CO2 injection)
- 100-200 md = Good
- 50-100 md = Moderate
- <50 md = Poor (difficult injection)

**Depth** (meters):
- >800m = Keeps CO2 in supercritical state (dense, efficient)
- 800-1200m = Ideal range
- 1200-2500m = Good but requires higher pressure
- >2500m = Deep (expensive drilling)

**Pressure** (megapascals, MPa):
- 8-50 MPa = Optimal range for supercritical CO2
- Related to depth (~1 MPa per 100m)

**Temperature** (Celsius):
- 31-120°C = Supercritical range (ideal)
- <31°C = Gaseous CO2 (less dense)

**Salinity** (parts per million, ppm):
- Higher = Better (unusable for drinking, no conflicts)
- 10,000-150,000 ppm = Typical range

**Risk Levels**:
- **LOW**: Safe for injection, minimal seismic activity, good regulatory environment
- **MEDIUM**: Monitor carefully, some mitigation needed
- **HIGH**: Avoid unless no alternatives, requires extensive mitigation

### Suitability Scoring Heuristics

**Ideal Storage Site**:
- Capacity: >500 Mt (can handle large-scale projects)
- Risk: LOW
- Depth: 800-2000m (supercritical CO2, not too expensive)
- Porosity: >0.18
- Permeability: >100 md
- Regulatory score: >0.7

**Acceptable Site**:
- Capacity: >100 Mt
- Risk: LOW or MEDIUM
- Depth: >800m
- Porosity: >0.12
- Permeability: >50 md

**Avoid**:
- Risk: HIGH
- Depth: <800m (CO2 won't stay supercritical)
- Permeability: <50 md (injection too difficult)

## Output Format

Generate a JSON object with this structure:

```json
{
    "summary": "2-3 sentence executive summary of findings",
    "insights": [
        {
            "title": "Concise insight title",
            "description": "Detailed explanation with numbers and context",
            "importance": "high" | "medium" | "low"
        }
    ],
    "recommendations": [
        {
            "action": "Specific action to take (e.g., 'Prioritize X aquifer for pilot study')",
            "rationale": "Why this action makes sense based on the data",
            "priority": "high" | "medium" | "low"
        }
    ],
    "data_quality_notes": "Any caveats about the data or analysis (optional)",
    "follow_up_questions": [
        "Specific question that would provide deeper insight"
    ],
    "visualization_hints": [
        {
            "type": "table" | "map" | "chart" | "stats",
            "data_key": "Key to access relevant data",
            "config": {
                "chart_type": "bar" | "scatter" | "line",
                "x_axis": "field name",
                "y_axis": "field name"
            }
        }
    ]
}
```

## Analysis Guidelines

### 1. Be Specific with Numbers
- ❌ "Several aquifers have high capacity"
- ✅ "5 aquifers exceed 500 Mt capacity, with the Amazon-347 leading at 892 Mt"

### 2. Provide Context
- ❌ "Porosity is 0.23"
- ✅ "Porosity of 0.23 is excellent - 23% of rock volume can store CO2"

### 3. Make Actionable Recommendations
- ❌ "Aquifer X has good properties"
- ✅ "Conduct feasibility study on Aquifer X - combines 650 Mt capacity, low risk, and optimal depth of 1200m"

### 4. Prioritize by User Intent
- Capacity query → Focus on top performers, compare metrics
- Risk query → Emphasize safety, regulatory compliance
- Location query → Consider geographic distribution, accessibility

### 5. Suggest Next Steps
- Technical: "Analyze seismic data for the top 3 candidates"
- Business: "Estimate drilling costs for depths >1500m"
- Comparative: "Compare these results with North American basins"

## Example Analysis

**User Query**: "Find aquifers with capacity >500 Mt and low risk"

**Results**: 3 aquifers found:
- Amazon-347: 892 Mt, depth 1200m, porosity 0.24, risk LOW
- Permian-521: 678 Mt, depth 1850m, porosity 0.19, risk LOW
- Santos-112: 540 Mt, depth 950m, porosity 0.21, risk LOW

**Good Analysis**:
```json
{
    "summary": "Found 3 high-capacity, low-risk aquifers suitable for large-scale CO2 storage projects. Amazon-347 stands out with exceptional capacity (892 Mt) and excellent porosity (0.24).",
    "insights": [
        {
            "title": "Amazon-347 is the top candidate",
            "description": "With 892 Mt capacity, this aquifer can store emissions from a large coal plant for 178+ years. Its porosity of 0.24 means efficient storage, and depth of 1200m keeps CO2 supercritical.",
            "importance": "high"
        },
        {
            "title": "All candidates meet safety requirements",
            "description": "All 3 aquifers have LOW risk ratings, indicating minimal seismic activity and favorable regulatory environments.",
            "importance": "high"
        }
    ],
    "recommendations": [
        {
            "action": "Prioritize Amazon-347 for detailed feasibility study",
            "rationale": "Highest capacity (892 Mt), excellent technical parameters, and optimal depth. Single site could handle multiple projects.",
            "priority": "high"
        },
        {
            "action": "Evaluate Permian-521 as backup option",
            "rationale": "Solid capacity (678 Mt) in a well-studied basin. Greater depth (1850m) may increase drilling costs but ensures supercritical storage.",
            "priority": "medium"
        }
    ],
    "follow_up_questions": [
        "What are the permeability values for these aquifers?",
        "Are there any existing wells or infrastructure near these sites?",
        "What is the regulatory timeline for CO2 injection permits in Brazil vs USA?"
    ],
    "visualization_hints": [
        {
            "type": "table",
            "data_key": "top_aquifers",
            "config": {
                "columns": ["name", "capacity", "depth", "porosity", "risk"],
                "sortable": true
            }
        },
        {
            "type": "map",
            "data_key": "aquifer_locations",
            "config": {
                "center_on": "results",
                "marker_size_by": "capacity"
            }
        }
    ]
}
```

Now analyze the provided query results and generate your report.
"""


def format_results_for_llm(validation_results: List[ValidationResult]) -> str:
    """
    Format validation results into a readable text for the LLM.

    Args:
        validation_results: List of validation results with query data

    Returns:
        Formatted string representation of results
    """
    if not validation_results:
        return "No data available."

    output_parts = []

    for i, vr in enumerate(validation_results, 1):
        output_parts.append(f"\n## Sub-task {vr.subtask_id} Results")

        if vr.status in [ValidationStatus.VALID, ValidationStatus.HEALED]:
            results = vr.results or []
            output_parts.append(f"Status: {vr.status.value}")
            output_parts.append(f"Execution time: {vr.execution_time_ms:.0f}ms")
            output_parts.append(f"Records returned: {len(results)}")

            if vr.healing_explanation:
                output_parts.append(f"Note: Query was auto-healed - {vr.healing_explanation}")

            if results:
                # Show first few results
                max_rows = 20
                output_parts.append(f"\n### Data (showing first {min(len(results), max_rows)} of {len(results)}):")

                for idx, record in enumerate(results[:max_rows], 1):
                    # Format record nicely
                    formatted_record = ", ".join(
                        f"{k}={v}" for k, v in record.items()
                        if v is not None
                    )
                    output_parts.append(f"{idx}. {formatted_record}")

                if len(results) > max_rows:
                    output_parts.append(f"... and {len(results) - max_rows} more records")
        else:
            output_parts.append(f"Status: {vr.status.value} - {vr.error_message}")

    return "\n".join(output_parts)


async def analyze_node(state: AgentState) -> AgentState:
    """
    Analyst Agent Node

    Synthesizes validation results into prescriptive insights and recommendations.

    Args:
        state: Current agent state with validation_results

    Returns:
        Updated state with analysis_report populated
    """
    start_time = datetime.utcnow()
    validation_results = state.get("validation_results", [])

    logger.info(f"[ANALYST] Analyzing results from {len(validation_results)} queries")

    # Check if we have any successful results
    successful_results = [
        vr for vr in validation_results
        if vr.status in [ValidationStatus.VALID, ValidationStatus.HEALED]
        and vr.results
    ]

    if not successful_results:
        logger.warning("[ANALYST] No successful results to analyze")

        # Create empty report
        empty_report = AnalysisReport(
            summary="No data was retrieved successfully. Please check the query or try rephrasing your question.",
            insights=[],
            recommendations=[
                Recommendation(
                    action="Try rephrasing your question or simplifying the query",
                    rationale="The database queries encountered errors or returned no results",
                    priority="high"
                )
            ],
            data_quality_notes="All queries failed validation or returned empty results",
            follow_up_questions=[
                "Could you rephrase your question?",
                "Would you like to see what data is available in the database?"
            ],
            visualization_hints=[]
        )

        state["analysis_report"] = empty_report
        return state

    try:
        llm = get_llm_client()

        # Format results for LLM
        results_text = format_results_for_llm(validation_results)

        # Count total records for context
        total_records = sum(len(vr.results or []) for vr in successful_results)

        # Build analysis prompt
        messages = [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": f"""Analyze these query results and provide prescriptive recommendations.

## User's Original Question
{state['user_query']}

## Query Complexity
{state.get('query_plan').complexity if state.get('query_plan') else 'Unknown'}

## Query Results
{results_text}

## Summary Stats
- Successful queries: {len(successful_results)}/{len(validation_results)}
- Total records retrieved: {total_records}
- Query healing required: {state.get('total_retries', 0)} times

Provide a comprehensive analysis with specific, actionable insights and recommendations.
Focus on what the user should DO based on this data.
"""}
        ]

        logger.debug("[ANALYST] Calling LLM for analysis...")

        # Generate structured analysis
        report = await llm.generate_structured(
            agent_name=AgentName.ANALYST,
            messages=messages,
            response_model=AnalysisReport,
            temperature=0.3  # Slightly higher for creative insights
        )

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"[ANALYST] Analysis complete: {len(report.insights)} insights, "
            f"{len(report.recommendations)} recommendations, {duration_ms:.0f}ms"
        )

        # Update state
        state["analysis_report"] = report

        # Add execution trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="analyst",
                timestamp=datetime.utcnow(),
                input={
                    "validation_results": len(validation_results),
                    "total_records": total_records
                },
                output=report.model_dump(),
                duration_ms=duration_ms,
                error=None
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state

    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"[ANALYST] Error during analysis: {e}", exc_info=True)

        # Create fallback report with basic insights
        total_records = sum(len(vr.results or []) for vr in successful_results)

        fallback_report = AnalysisReport(
            summary=f"Analysis completed. Retrieved {total_records} records from {len(successful_results)} successful queries.",
            insights=[
                Insight(
                    title="Data Retrieved Successfully",
                    description=f"Found {total_records} records matching your criteria",
                    importance="medium"
                )
            ],
            recommendations=[
                Recommendation(
                    action="Review the raw results in Expert Mode",
                    rationale="Automated analysis encountered an error, but data was retrieved successfully",
                    priority="medium"
                )
            ],
            data_quality_notes=f"Automated analysis failed: {str(e)[:100]}",
            follow_up_questions=["What specific aspect would you like me to analyze?"],
            visualization_hints=[
                VisualizationHint(
                    type="table",
                    data_key="results",
                    config={"default_view": True}
                )
            ]
        )

        state["analysis_report"] = fallback_report
        state["error_count"] = state.get("error_count", 0) + 1

        # Add error trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="analyst",
                timestamp=datetime.utcnow(),
                input={"validation_results": len(validation_results)},
                output=fallback_report.model_dump(),
                duration_ms=duration_ms,
                error=str(e)
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state
