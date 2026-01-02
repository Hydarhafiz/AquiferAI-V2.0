"""
Cypher Specialist Agent for AquiferAI V2.0

Generates Neo4j Cypher queries for each sub-task in the execution plan.

Key responsibilities:
1. Translate natural language sub-tasks into Cypher queries
2. Follow schema constraints and best practices
3. Generate parameterized queries where appropriate
4. Include explanations for each query
5. Identify expected result columns

The specialist has deep knowledge of the aquifer database schema
and Neo4j query optimization patterns.
"""

import logging
from typing import List
from datetime import datetime

from app.graph.state import (
    AgentState,
    CypherQuery,
    QueryPlan,
    SubTask,
    ExecutionTraceStep
)
from app.core.llm_provider import get_llm_client, AgentName

logger = logging.getLogger(__name__)


CYPHER_SPECIALIST_PROMPT = """You are the Cypher Specialist Agent for a Neo4j-based saline aquifer database.

## Database Schema

```
(:Aquifer {
    name: STRING,
    depth_m: FLOAT,
    porosity: FLOAT,
    permeability_md: FLOAT,
    temperature_c: FLOAT,
    pressure_mpa: FLOAT,
    salinity_ppm: INTEGER,
    co2_storage_capacity_mt: FLOAT,
    latitude: FLOAT,
    longitude: FLOAT,
    cluster_id: INTEGER
})

(:Basin {
    name: STRING,
    area_km2: FLOAT
})

(:Country {
    name: STRING,
    region: STRING
})

(:RiskAssessment {
    risk_level: STRING,      # LOW, MEDIUM, HIGH
    seismic_risk: STRING,    # LOW, MEDIUM, HIGH
    regulatory_score: FLOAT  # 0.0 to 1.0
})

Relationships:
(Aquifer)-[:LOCATED_IN]->(Basin)
(Basin)-[:WITHIN]->(Country)
(Aquifer)-[:HAS_RISK]->(RiskAssessment)
```

## Query Writing Rules

### MUST Follow:
1. **Always use RETURN clause** - Every query must have RETURN
2. **Use LIMIT for safety** - Default LIMIT 20 for unbounded queries
3. **Property names are case-sensitive** - Use exact casing from schema
4. **Use OPTIONAL MATCH** for potentially missing relationships
5. **Parameterize user input** - Use $parameters for dynamic values
6. **Explicit relationships** - Use full relationship syntax: -[:RELATIONSHIP]->

### Best Practices:
- **Performance**: Add indexes to WHERE clauses where possible
- **Readability**: Use clear aliases (a for Aquifer, b for Basin, etc.)
- **Safety**: Avoid unbounded traversals (MATCH (n)-[*]->())
- **Completeness**: Include all relevant properties in RETURN

### Common Patterns:

**Single aquifer lookup:**
```cypher
MATCH (a:Aquifer {name: $aquifer_name})
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
OPTIONAL MATCH (a)-[:HAS_RISK]->(r:RiskAssessment)
RETURN a, b, r
```

**Aquifers in a basin:**
```cypher
MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin {name: $basin_name})
OPTIONAL MATCH (a)-[:HAS_RISK]->(r:RiskAssessment)
RETURN a, b, r
LIMIT 20
```

**Top N by capacity:**
```cypher
MATCH (a:Aquifer)
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
OPTIONAL MATCH (a)-[:HAS_RISK]->(r:RiskAssessment)
RETURN a, b, r
ORDER BY a.co2_storage_capacity_mt DESC
LIMIT $limit
```

**Filter by risk level:**
```cypher
MATCH (a:Aquifer)-[:HAS_RISK]->(r:RiskAssessment {risk_level: $risk_level})
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
RETURN a, b, r
LIMIT 20
```

**Aggregation (count by country):**
```cypher
MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin)-[:WITHIN]->(c:Country)
RETURN c.name as country, count(a) as aquifer_count
ORDER BY aquifer_count DESC
```

**Complex filtering (capacity + risk + depth):**
```cypher
MATCH (a:Aquifer)-[:HAS_RISK]->(r:RiskAssessment)
WHERE a.co2_storage_capacity_mt >= $min_capacity
  AND r.risk_level = $risk_level
  AND a.depth_m BETWEEN $min_depth AND $max_depth
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
RETURN a, b, r
ORDER BY a.co2_storage_capacity_mt DESC
LIMIT 10
```

## Output Format

For each sub-task, respond with JSON:
```json
{
    "subtask_id": <ID from the plan>,
    "cypher": "<valid Cypher query>",
    "explanation": "Plain English: what this query does and why",
    "parameters": {
        "param_name": "description of expected value"
    },
    "expected_columns": ["column1", "column2", ...]
}
```

## Important Notes

- **NO placeholders**: If a specific value is mentioned (e.g., "Solimões"), hardcode it in the query
- **Use parameters**: Only use parameters for generic filters (e.g., $limit, $min_capacity)
- **Be defensive**: Use OPTIONAL MATCH when relationships might not exist
- **Think performance**: Avoid queries that could return thousands of results
- **Return metadata**: Include related entities (Basin, RiskAssessment) for context

Now generate a Cypher query for the given sub-task.
"""


async def generate_cypher_node(state: AgentState) -> AgentState:
    """
    Cypher Specialist Agent Node

    Generates Cypher queries for each sub-task in the query plan.

    Args:
        state: Current agent state with query_plan

    Returns:
        Updated state with generated_queries populated
    """
    start_time = datetime.utcnow()
    plan: QueryPlan = state.get("query_plan")

    if not plan:
        logger.error("[CYPHER] No query plan found in state")
        state["error_count"] = state.get("error_count", 0) + 1
        return state

    logger.info(f"[CYPHER] Generating queries for {len(plan.subtasks)} sub-tasks")

    try:
        llm = get_llm_client()
        generated_queries: List[CypherQuery] = []

        for subtask in plan.subtasks:
            logger.debug(f"[CYPHER] Processing subtask {subtask.id}: {subtask.description}")

            # Build context-aware prompt
            messages = [
                {"role": "system", "content": CYPHER_SPECIALIST_PROMPT},
                {"role": "user", "content": f"""Generate a Cypher query for this sub-task:

**Sub-task ID**: {subtask.id}
**Description**: {subtask.description}
**Expected Output**: {subtask.expected_output}
**Dependencies**: {subtask.dependencies}

**Original User Query**: {state['user_query']}

**Query Complexity**: {plan.complexity}

Generate the Cypher query following all the rules and best practices.
"""}
            ]

            try:
                # Generate structured query
                query = await llm.generate_structured(
                    agent_name=AgentName.CYPHER_SPECIALIST,
                    messages=messages,
                    response_model=CypherQuery,
                    temperature=0.1  # Low temperature for precise query generation
                )

                logger.info(f"[CYPHER] Generated query for subtask {subtask.id}: {query.cypher[:60]}...")
                generated_queries.append(query)

            except Exception as e:
                logger.error(f"[CYPHER] Error generating query for subtask {subtask.id}: {e}")

                # Create fallback query
                fallback_query = CypherQuery(
                    subtask_id=subtask.id,
                    cypher="MATCH (a:Aquifer) RETURN a LIMIT 10",
                    explanation=f"Fallback query due to error: {str(e)[:100]}",
                    parameters={},
                    expected_columns=["a"]
                )
                generated_queries.append(fallback_query)
                state["error_count"] = state.get("error_count", 0) + 1

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"[CYPHER] Generated {len(generated_queries)} queries in {duration_ms:.0f}ms"
        )

        # Update state
        state["generated_queries"] = generated_queries

        # Add execution trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="cypher-specialist",
                timestamp=datetime.utcnow(),
                input={"plan": plan.model_dump()},
                output={"queries": [q.model_dump() for q in generated_queries]},
                duration_ms=duration_ms,
                error=None
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state

    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"[CYPHER] Critical error: {e}", exc_info=True)

        # Create minimal fallback
        state["generated_queries"] = [
            CypherQuery(
                subtask_id=1,
                cypher="MATCH (a:Aquifer) RETURN a.name, a.co2_storage_capacity_mt LIMIT 10",
                explanation="Emergency fallback query",
                parameters={},
                expected_columns=["a.name", "a.co2_storage_capacity_mt"]
            )
        ]
        state["error_count"] = state.get("error_count", 0) + 1

        # Add error trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="cypher-specialist",
                timestamp=datetime.utcnow(),
                input={"plan": plan.model_dump() if plan else {}},
                output={"queries": []},
                duration_ms=duration_ms,
                error=str(e)
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state
