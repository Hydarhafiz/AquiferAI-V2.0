"""
Planner Agent for AquiferAI V2.0

Analyzes user queries and creates execution plans by:
1. Classifying query complexity (SIMPLE, COMPOUND, ANALYTICAL)
2. Decomposing into executable sub-tasks
3. Identifying dependencies between tasks
4. Estimating execution time

The Planner uses schema knowledge to understand what data is available
and creates a structured plan for the Cypher Specialist to implement.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from app.graph.state import (
    AgentState,
    QueryPlan,
    SubTask,
    QueryComplexity,
    ExecutionTraceStep
)
from app.core.llm_provider import get_llm_client, AgentName

logger = logging.getLogger(__name__)


# Neo4j Schema for AquiferAI
NEO4J_SCHEMA = """
## Neo4j Database Schema

### Node Labels and Properties

**Aquifer**
- name: STRING (unique identifier)
- depth_m: FLOAT (depth in meters)
- porosity: FLOAT (porosity coefficient, 0-1)
- permeability_md: FLOAT (permeability in millidarcies)
- temperature_c: FLOAT (temperature in Celsius)
- pressure_mpa: FLOAT (pressure in megapascals)
- salinity_ppm: INTEGER (salinity in parts per million)
- co2_storage_capacity_mt: FLOAT (CO2 storage capacity in megatonnes)
- latitude: FLOAT
- longitude: FLOAT
- cluster_id: INTEGER (clustering result)

**Basin**
- name: STRING (basin name)
- area_km2: FLOAT (area in square kilometers)

**Country**
- name: STRING (country name)
- region: STRING (geographic region)

**RiskAssessment**
- risk_level: STRING (LOW, MEDIUM, HIGH)
- seismic_risk: STRING (LOW, MEDIUM, HIGH)
- regulatory_score: FLOAT (0.0 to 1.0)

### Relationships

- (Aquifer)-[:LOCATED_IN]->(Basin)
- (Basin)-[:WITHIN]->(Country)
- (Aquifer)-[:HAS_RISK]->(RiskAssessment)

### Query Patterns

**Simple queries** (1 sub-task):
- Single aquifer lookup by name
- List aquifers in a basin
- Count queries

**Compound queries** (2-3 sub-tasks):
- Compare aquifers across basins
- Filter by multiple properties
- Find relationships between entities

**Analytical queries** (3+ sub-tasks):
- Rankings and top-N selection
- Risk analysis with thresholds
- Geographic clustering
- Capacity planning with constraints
"""


PLANNER_SYSTEM_PROMPT = f"""You are the Planner Agent for a saline aquifer CO2 storage analytics system.

Your mission is to analyze user questions and create a structured execution plan.

{NEO4J_SCHEMA}

## Classification Rules

Classify the query as:

**SIMPLE**: Direct lookups or basic filters
- Examples: "Show me the Solimões aquifer", "List aquifers in Brazil"
- Sub-tasks: 1
- Pattern: Single MATCH query

**COMPOUND**: Multiple entities or comparisons
- Examples: "Compare aquifers in Amazon Basin vs Permian Basin"
- Sub-tasks: 2-3
- Pattern: Multiple MATCH queries, possibly with aggregation

**ANALYTICAL**: Complex analysis requiring synthesis
- Examples: "Recommend best sites for 500 Mt CO2 storage project"
- Sub-tasks: 3-5
- Pattern: Multiple queries + filtering + ranking + analysis

## Output Format

Respond with a JSON object matching this structure:
{{
    "complexity": "SIMPLE" | "COMPOUND" | "ANALYTICAL",
    "subtasks": [
        {{
            "id": 1,
            "description": "Clear description of what to fetch",
            "dependencies": [<list of subtask IDs that must complete first>],
            "expected_output": "Type of data expected (e.g., 'list of aquifers', 'count', 'aggregated stats')"
        }}
    ],
    "reasoning": "Brief explanation of your planning decision",
    "estimated_execution_time": <seconds as float>
}}

## Important Guidelines

1. **Be specific**: Each subtask should map to a single Cypher query
2. **Dependencies**: Use dependencies when one query needs results from another
3. **Granularity**: Break complex questions into atomic operations
4. **Schema awareness**: Only plan for data that exists in the schema
5. **Estimation**: Simple=2s, Compound=5s, Analytical=10s (baseline, can adjust)

## Examples

Query: "What is the storage capacity of Solimões aquifer?"
{{
    "complexity": "SIMPLE",
    "subtasks": [
        {{
            "id": 1,
            "description": "Retrieve storage capacity for Solimões aquifer",
            "dependencies": [],
            "expected_output": "single aquifer with capacity"
        }}
    ],
    "reasoning": "Direct lookup by name, single property retrieval",
    "estimated_execution_time": 2.0
}}

Query: "Compare top 5 aquifers in Amazon Basin vs Permian Basin by capacity"
{{
    "complexity": "COMPOUND",
    "subtasks": [
        {{
            "id": 1,
            "description": "Get top 5 aquifers in Amazon Basin ordered by capacity",
            "dependencies": [],
            "expected_output": "list of 5 aquifers with capacity"
        }},
        {{
            "id": 2,
            "description": "Get top 5 aquifers in Permian Basin ordered by capacity",
            "dependencies": [],
            "expected_output": "list of 5 aquifers with capacity"
        }}
    ],
    "reasoning": "Two independent queries for different basins, results will be compared",
    "estimated_execution_time": 5.0
}}

Query: "Recommend the best aquifer for a 500 Mt CO2 storage project with low seismic risk"
{{
    "complexity": "ANALYTICAL",
    "subtasks": [
        {{
            "id": 1,
            "description": "Find aquifers with capacity >= 500 Mt",
            "dependencies": [],
            "expected_output": "list of high-capacity aquifers"
        }},
        {{
            "id": 2,
            "description": "Filter for low seismic risk from task 1 results",
            "dependencies": [1],
            "expected_output": "filtered list with risk data"
        }},
        {{
            "id": 3,
            "description": "Rank by depth, porosity, and permeability (optimal conditions)",
            "dependencies": [2],
            "expected_output": "ranked list with technical parameters"
        }}
    ],
    "reasoning": "Multi-stage filtering and ranking based on capacity threshold, risk level, and technical suitability",
    "estimated_execution_time": 8.0
}}

Now analyze the user's query and create an execution plan.
"""


async def plan_node(state: AgentState) -> AgentState:
    """
    Planner Agent Node

    Analyzes the user query and creates an execution plan with sub-tasks.

    Args:
        state: Current agent state with user_query

    Returns:
        Updated state with query_plan populated
    """
    start_time = datetime.utcnow()
    user_query = state["user_query"]

    logger.info(f"[PLANNER] Processing query: '{user_query}'")

    try:
        # Get LLM client
        llm = get_llm_client()

        # Build messages
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this query and create an execution plan:\n\n{user_query}"}
        ]

        # Generate structured plan
        logger.debug("[PLANNER] Calling LLM for query planning...")
        plan = await llm.generate_structured(
            agent_name=AgentName.PLANNER,
            messages=messages,
            response_model=QueryPlan,
            temperature=0.1  # Low temperature for deterministic planning
        )

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"[PLANNER] Plan created: complexity={plan.complexity}, "
            f"subtasks={len(plan.subtasks)}, duration={duration_ms:.0f}ms"
        )

        # Update state
        state["query_plan"] = plan

        # Add execution trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="planner",
                timestamp=datetime.utcnow(),
                input={"user_query": user_query},
                output=plan.model_dump(),
                duration_ms=duration_ms,
                error=None
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state

    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"[PLANNER] Error during planning: {e}", exc_info=True)

        # Create fallback simple plan
        logger.warning("[PLANNER] Creating fallback simple plan")
        fallback_plan = QueryPlan(
            complexity=QueryComplexity.SIMPLE,
            subtasks=[
                SubTask(
                    id=1,
                    description=user_query,
                    dependencies=[],
                    expected_output="data"
                )
            ],
            reasoning=f"Fallback plan due to error: {str(e)[:100]}",
            estimated_execution_time=3.0
        )

        state["query_plan"] = fallback_plan
        state["error_count"] = state.get("error_count", 0) + 1

        # Add error trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="planner",
                timestamp=datetime.utcnow(),
                input={"user_query": user_query},
                output=fallback_plan.model_dump(),
                duration_ms=duration_ms,
                error=str(e)
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state
