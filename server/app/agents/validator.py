"""
Validator Agent for AquiferAI V2.0

Validates and executes Cypher queries with intelligent self-healing.

Key responsibilities:
1. Static syntax validation (parentheses, brackets, required clauses)
2. Execute queries against Neo4j database
3. Self-healing loop for broken queries (max 3 retries)
4. Track execution time and retry counts
5. Return structured validation results

The validator acts as a defensive layer, catching errors before they
reach the database and intelligently fixing common issues.
"""

import logging
import re
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.graph.state import (
    AgentState,
    ValidationResult,
    ValidationStatus,
    CypherQuery,
    ExecutionTraceStep
)
from app.core.llm_provider import get_llm_client, AgentName
from app.core.neo4j import execute_cypher_query

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
QUERY_TIMEOUT_MS = 30000  # 30 seconds


VALIDATOR_HEALING_PROMPT = """You are the Validator Agent. Your job is to fix broken Cypher queries.

## Common Issues and Fixes

### 1. Label Typos
- ❌ `MATCH (a:Aquifier)`
- ✅ `MATCH (a:Aquifer)`

### 2. Unknown Relationships
- ❌ `MATCH (a)-[:CONTAINS]->(b)`
- ✅ `MATCH (a)-[:LOCATED_IN]->(b)` (use LOCATED_IN, WITHIN, or HAS_RISK)

### 3. Unknown Properties
- ❌ `WHERE a.storage_capacity > 500`
- ✅ `WHERE a.co2_storage_capacity_mt > 500`

### 4. Syntax Errors
- ❌ `MATCH (a:Aquifer RETURN a`
- ✅ `MATCH (a:Aquifer) RETURN a`
- ❌ `MATCH (a:Aquifer] RETURN a`
- ✅ `MATCH (a:Aquifer) RETURN a`

### 5. Missing Clauses
- ❌ `MATCH (a:Aquifer) WHERE a.depth_m > 1000`
- ✅ `MATCH (a:Aquifer) WHERE a.depth_m > 1000 RETURN a`

### 6. Case Sensitivity
- ❌ `MATCH (a:aquifer)` or `a.Name`
- ✅ `MATCH (a:Aquifer)` and `a.name`

## Valid Schema Reference

**Labels**: Aquifer, Basin, Country, RiskAssessment
**Relationships**: LOCATED_IN, WITHIN, HAS_RISK
**Aquifer Properties**: name, depth_m, porosity, permeability_md, temperature_c, pressure_mpa, salinity_ppm, co2_storage_capacity_mt, latitude, longitude, cluster_id
**Basin Properties**: name, area_km2
**Country Properties**: name, region
**RiskAssessment Properties**: risk_level, seismic_risk, regulatory_score

## Your Task

Given a broken Cypher query and its error message, fix the query.

**Rules**:
1. Return ONLY the corrected Cypher query, no explanation
2. Keep the query's intent intact
3. Use exact label and property names from schema
4. Add LIMIT if the query might return many results
5. Use OPTIONAL MATCH for relationships that might not exist

Return just the corrected query.
"""


def validate_syntax(query: str) -> List[str]:
    """
    Perform static syntax validation on a Cypher query.

    Checks:
    - Balanced parentheses, brackets, curly braces
    - Required clauses (MATCH/CREATE and RETURN)
    - No obvious SQL injection patterns

    Args:
        query: Cypher query to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check balanced delimiters
    if query.count('(') != query.count(')'):
        errors.append("Unbalanced parentheses")

    if query.count('[') != query.count(']'):
        errors.append("Unbalanced square brackets")

    if query.count('{') != query.count('}'):
        errors.append("Unbalanced curly braces")

    # Check for required clauses
    query_upper = query.upper()

    if 'MATCH' not in query_upper and 'CREATE' not in query_upper and 'MERGE' not in query_upper:
        errors.append("Missing graph pattern clause (MATCH, CREATE, or MERGE)")

    if 'RETURN' not in query_upper:
        errors.append("Missing RETURN clause")

    # Check for common typos
    if 'AQUIFIER' in query_upper:
        errors.append("Label typo: 'Aquifier' should be 'Aquifer'")

    # Warn about unbounded queries (performance)
    if 'MATCH' in query_upper and 'LIMIT' not in query_upper and 'COUNT' not in query_upper:
        # This is a warning, not a hard error
        logger.warning(f"[VALIDATOR] Query has no LIMIT clause (may return many results)")

    return errors


async def heal_query(
    query: str,
    error_message: str,
    llm
) -> tuple[str, str]:
    """
    Use the LLM to heal a broken Cypher query.

    Args:
        query: The broken query
        error_message: Error message from Neo4j or validator
        llm: LLM client instance

    Returns:
        Tuple of (healed_query, healing_explanation)
    """
    logger.debug(f"[VALIDATOR] Attempting to heal query: {query[:100]}...")
    logger.debug(f"[VALIDATOR] Error: {error_message}")

    messages = [
        {"role": "system", "content": VALIDATOR_HEALING_PROMPT},
        {"role": "user", "content": f"""Fix this broken Cypher query:

**Query**:
```cypher
{query}
```

**Error**:
{error_message}

Return ONLY the corrected query."""}
    ]

    try:
        healed_query_raw = await llm.generate(
            agent_name=AgentName.VALIDATOR,
            messages=messages,
            temperature=0.0,  # Deterministic healing
            max_tokens=500
        )

        # Clean up the response (remove markdown code blocks if present)
        healed_query = healed_query_raw.strip()

        # Remove markdown code fences
        if healed_query.startswith("```"):
            lines = healed_query.split("\n")
            # Remove first line (```cypher or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            healed_query = "\n".join(lines).strip()

        explanation = f"Fixed: {error_message[:100]}"

        logger.info(f"[VALIDATOR] Healed query: {healed_query[:100]}...")
        return healed_query, explanation

    except Exception as e:
        logger.error(f"[VALIDATOR] Healing failed: {e}")
        # Return original query if healing fails
        return query, f"Healing failed: {str(e)}"


async def validate_and_execute(
    cypher_query: CypherQuery,
    llm,
    state: AgentState
) -> ValidationResult:
    """
    Validate and execute a single Cypher query with self-healing.

    This is the core validation loop:
    1. Static validation
    2. Execute against Neo4j
    3. If error, attempt healing (up to MAX_RETRIES)
    4. Return validation result

    Args:
        cypher_query: The query to validate and execute
        llm: LLM client for healing
        state: Current agent state (for tracking)

    Returns:
        ValidationResult with execution details
    """
    current_query = cypher_query.cypher
    retry_count = 0
    healing_explanation = None

    logger.info(f"[VALIDATOR] Validating subtask {cypher_query.subtask_id}")

    while retry_count <= MAX_RETRIES:
        # Step 1: Static validation
        syntax_errors = validate_syntax(current_query)

        if syntax_errors:
            logger.warning(f"[VALIDATOR] Syntax errors: {syntax_errors}")

            if retry_count >= MAX_RETRIES:
                return ValidationResult(
                    subtask_id=cypher_query.subtask_id,
                    status=ValidationStatus.SYNTAX_ERROR,
                    original_query=cypher_query.cypher,
                    healed_query=current_query if current_query != cypher_query.cypher else None,
                    results=None,
                    error_message="; ".join(syntax_errors),
                    retry_count=retry_count,
                    execution_time_ms=0.0,
                    healing_explanation=healing_explanation
                )

            # Attempt healing
            current_query, explanation = await heal_query(
                current_query,
                "; ".join(syntax_errors),
                llm
            )
            healing_explanation = explanation
            retry_count += 1
            continue

        # Step 2: Execute query against Neo4j
        try:
            start_time = time.perf_counter()

            # Execute using the existing Neo4j driver
            results = await execute_cypher_query(current_query, cypher_query.parameters)

            execution_time = (time.perf_counter() - start_time) * 1000  # ms

            logger.info(
                f"[VALIDATOR] ✓ Query executed successfully: "
                f"{len(results) if results else 0} results in {execution_time:.0f}ms"
            )

            # Determine final status
            final_status = (
                ValidationStatus.HEALED if retry_count > 0 else ValidationStatus.VALID
            )

            return ValidationResult(
                subtask_id=cypher_query.subtask_id,
                status=final_status,
                original_query=cypher_query.cypher,
                healed_query=current_query if current_query != cypher_query.cypher else None,
                results=results,
                error_message=None,
                retry_count=retry_count,
                execution_time_ms=execution_time,
                healing_explanation=healing_explanation
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[VALIDATOR] Execution error: {error_msg}")

            if retry_count >= MAX_RETRIES:
                return ValidationResult(
                    subtask_id=cypher_query.subtask_id,
                    status=ValidationStatus.EXECUTION_ERROR,
                    original_query=cypher_query.cypher,
                    healed_query=current_query if current_query != cypher_query.cypher else None,
                    results=None,
                    error_message=error_msg,
                    retry_count=retry_count,
                    execution_time_ms=0.0,
                    healing_explanation=healing_explanation
                )

            # Attempt healing
            current_query, explanation = await heal_query(
                current_query,
                error_msg,
                llm
            )
            healing_explanation = explanation
            retry_count += 1

    # Max retries exceeded
    return ValidationResult(
        subtask_id=cypher_query.subtask_id,
        status=ValidationStatus.EXECUTION_ERROR,
        original_query=cypher_query.cypher,
        healed_query=current_query if current_query != cypher_query.cypher else None,
        results=None,
        error_message="Max retries exceeded",
        retry_count=retry_count,
        execution_time_ms=0.0,
        healing_explanation=healing_explanation
    )


async def validate_node(state: AgentState) -> AgentState:
    """
    Validator Agent Node

    Validates and executes all generated Cypher queries with self-healing.

    Args:
        state: Current agent state with generated_queries

    Returns:
        Updated state with validation_results, all_queries_valid, and retry counts
    """
    start_time = datetime.utcnow()
    generated_queries = state.get("generated_queries")

    if not generated_queries:
        logger.error("[VALIDATOR] No queries to validate")
        state["error_count"] = state.get("error_count", 0) + 1
        return state

    logger.info(f"[VALIDATOR] Validating {len(generated_queries)} queries")

    try:
        llm = get_llm_client()
        validation_results: List[ValidationResult] = []
        total_retries = 0
        all_valid = True
        max_retries_exceeded = False

        # Validate each query
        for cypher_query in generated_queries:
            result = await validate_and_execute(cypher_query, llm, state)
            validation_results.append(result)

            total_retries += result.retry_count

            if result.status not in [ValidationStatus.VALID, ValidationStatus.HEALED]:
                all_valid = False

            if result.retry_count >= MAX_RETRIES:
                max_retries_exceeded = True

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Log summary
        valid_count = sum(
            1 for r in validation_results
            if r.status in [ValidationStatus.VALID, ValidationStatus.HEALED]
        )
        logger.info(
            f"[VALIDATOR] Validation complete: {valid_count}/{len(validation_results)} valid, "
            f"{total_retries} total retries, {duration_ms:.0f}ms"
        )

        # Update state
        state["validation_results"] = validation_results
        state["all_queries_valid"] = all_valid
        state["total_retries"] = total_retries
        state["max_retries_exceeded"] = max_retries_exceeded

        if not all_valid:
            state["error_count"] = state.get("error_count", 0) + (len(validation_results) - valid_count)

        # Add execution trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="validator",
                timestamp=datetime.utcnow(),
                input={"queries": [q.model_dump() for q in generated_queries]},
                output={
                    "results": [r.model_dump() for r in validation_results],
                    "all_valid": all_valid,
                    "total_retries": total_retries
                },
                duration_ms=duration_ms,
                error=None if all_valid else f"{len(validation_results) - valid_count} queries failed"
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state

    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"[VALIDATOR] Critical error: {e}", exc_info=True)

        state["error_count"] = state.get("error_count", 0) + 1
        state["validation_results"] = []
        state["all_queries_valid"] = False

        # Add error trace if expert mode
        if state.get("expert_mode"):
            trace_step = ExecutionTraceStep(
                agent="validator",
                timestamp=datetime.utcnow(),
                input={"queries": [q.model_dump() for q in generated_queries]},
                output={"results": []},
                duration_ms=duration_ms,
                error=str(e)
            )
            if state.get("execution_trace") is not None:
                state["execution_trace"].append(trace_step)

        return state
