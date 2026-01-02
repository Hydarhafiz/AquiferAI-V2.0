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

**Nodes:**
* `:Aquifer` properties: `OBJECTID` (STRING), `AquiferHydrogeologicClassification`, `Basin`, `Boundary_coordinates`, `Cluster`, `Continent`, `Country`, `Depth`, `Lake_area`, `Location` (Point WKT), `Parameter_area`, `Parameter_shape`, `Permeability`, `Porosity`, `Recharge`, `Thickness`
* `:Basin` properties: `name`
* `:Country` properties: `name`
* `:Continent` properties: `name`

**Relationships:**
* `(:Aquifer)-[:LOCATED_IN_BASIN]->(:Basin)`
* `(:Aquifer)-[:PART_OF]->(:Cluster)`
* `(:Basin)-[:IS_LOCATED_IN_COUNTRY]->(:Country)`
* `(:Country)-[:LOCATED_IN_CONTINENT]->(:Continent)`

## Query Generation Rules

1.  **Always return Cypher queries in a code block.**
2.  **Prioritize Geographic Filtering:** If a user mentions a basin, country, or continent name, **always use the appropriate full-text search first** to find relevant aquifers.
3.  **Access properties directly:** `a.PropertyName`.
4.  **For `OBJECTID` queries:** Use `MATCH (a:Aquifer {OBJECTID: "objectid"})`. Only use this if a specific `OBJECTID` is provided. NOTE: OBJECTID is in string format.
5.  **Always return all core aquifer properties essential for CO2 storage analysis**, including `a.Porosity`, `a.Permeability`, `a.Thickness`, `a.Depth`, `a.Recharge`, `a.Lake_area`, `a.Parameter_area`, `a.AquiferHydrogeologicClassification`, `a.Boundary_coordinates`, `a.Cluster`, `a.Location`, `a.Parameter_shape`, and `a.OBJECTID`, regardless of whether the user explicitly mentions them.
6.  **Always use explicit `RETURN` clauses** with specific property names. Include `a.OBJECTID` in all `RETURN` clauses.
7.  **Do not perform calculations or transformations in RETURN clause**. Only return existing properties.
8.  **Use `OPTIONAL MATCH`** for relationships to avoid missing results.
9.  **Avoid:**
    * Map projections (`a { .* }`)
    * `CREATE`, `SET`, `DELETE` operations
10.  **Geographic Search (Basin, Country, Continent):**
    * Use **full-text search** for any geographic name (basin, country, continent).
    * Always chain searches for multiple geographic terms.
    * **Always include `YIELD node AS X, score` followed by `WHERE score > 0.5` to ensure relevance.**
    * **Distinguish between single-entity focus and comparison:**
        * **For queries focusing on a *single* specific entity** (e.g., "the X basin"): After `WHERE score > 0.5`, **always add `ORDER BY score DESC LIMIT 1`**.
        * **For *comparison* queries** (e.g., "Compare X and Y"): **DO NOT use `LIMIT 1`** after `WHERE score > 0.5`.
    * When using full-text search for `basin`, always use the directly yielded `basin` node: `MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(basin)`.
11.  **Range Queries:** Express numerical ranges using comparison operators (`>=`, `<=`, `>`, `<`) combined with `AND`.
12. **Variable Scope with `WITH` clauses:**
    * Explicitly carry forward all **node variables** needed in subsequent clauses.
    * If carrying forward **properties**, alias them using `AS`.
13.  **Do not add `LIMIT` unless the user explicitly requests a specific number** (e.g., "top 5", "how many").

## Common Query Patterns

**Aquifers in a specific basin (single-entity focus):**
```cypher
CALL db.index.fulltext.queryNodes("basinSearch", $basin_name)
YIELD node AS basin, score
WHERE score > 0.5
ORDER BY score DESC
LIMIT 1
MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(basin)
RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Thickness, a.Depth, a.Recharge, basin.name AS basin_name
```

**Aquifer by OBJECTID:**
```cypher
MATCH (a:Aquifer {OBJECTID: $objectid})
RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Thickness, a.Depth, a.Recharge
```

**Aquifers in a country:**
```cypher
CALL db.index.fulltext.queryNodes("countrySearch", $country_name)
YIELD node AS country, score
WHERE score > 0.5
ORDER BY score DESC
LIMIT 1
MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(b)-[:IS_LOCATED_IN_COUNTRY]->(country)
RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Thickness, country.name AS country_name
```

**Compare basins (no LIMIT 1):**
```cypher
WITH ['Amazon', 'Parnaiba'] AS basinNames
UNWIND basinNames AS basinName
CALL db.index.fulltext.queryNodes("basinSearch", basinName)
YIELD node AS matchedBasin, score
WHERE score > 0.5
MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(matchedBasin)
RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Thickness, a.Depth, matchedBasin.name AS basin_name
ORDER BY basin_name
```

## Output Format

Respond with JSON:
```json
{
    "subtask_id": <ID>,
    "cypher": "<valid Cypher query>",
    "explanation": "What this query does",
    "parameters": {},
    "expected_columns": ["column1", "column2"]
}
```

## Important Notes

- **NO placeholders**: Hardcode specific values mentioned in queries
- **Use parameters** only for generic filters
- **Use OPTIONAL MATCH** when relationships might not exist
- **Think performance**: Avoid queries that could return thousands of results
- **Return all core properties**: Always include OBJECTID, Porosity, Permeability, Thickness, Depth, Recharge

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

                # Create fallback query with correct schema
                fallback_query = CypherQuery(
                    subtask_id=subtask.id,
                    cypher="MATCH (a:Aquifer) RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Depth LIMIT 10",
                    explanation=f"Fallback query due to error: {str(e)[:100]}",
                    parameters={},
                    expected_columns=["a.OBJECTID", "a.Porosity", "a.Permeability", "a.Depth"]
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

        # Create minimal fallback with correct schema
        state["generated_queries"] = [
            CypherQuery(
                subtask_id=1,
                cypher="MATCH (a:Aquifer) RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Depth LIMIT 10",
                explanation="Emergency fallback query",
                parameters={},
                expected_columns=["a.OBJECTID", "a.Porosity", "a.Permeability", "a.Depth"]
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
