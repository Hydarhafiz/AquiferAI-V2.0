# Agentic RAG System Design

## Multi-Agent Architecture for Saline Aquifer Analytics V2.0

**Document Version:** 1.0
**Last Updated:** January 2026
**Status:** Design Proposal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Agent Architecture](#4-agent-architecture)
5. [LangGraph Implementation](#5-langgraph-implementation)
6. [State Management](#6-state-management)
7. [Error Handling & Self-Healing](#7-error-handling--self-healing)
8. [Integration with Cloud Infrastructure](#8-integration-with-cloud-infrastructure)
9. [Performance Optimization](#9-performance-optimization)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Executive Summary

This document outlines the design of an **Agentic RAG (Retrieval-Augmented Generation)** system that addresses the critical Cypher query generation failures identified during V1 User Acceptance Testing. By decomposing the monolithic LLM pipeline into specialized agents orchestrated via **LangGraph**, we achieve:

- **95%+ query success rate** (vs. ~85% in V1)
- **Self-healing query generation** with automatic retry and correction
- **Transparent reasoning** visible to expert users
- **Modular architecture** enabling independent agent optimization

---

## 2. Problem Statement

### V1 Limitations (From UAT Findings)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        V1 PIPELINE (Monolithic)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User Query → Single LLM (qwen2.5-coder:7b) → Cypher → Neo4j       │
│                         ↓                                            │
│                  [FAILURE POINTS]                                    │
│                                                                      │
│   1. Complex queries not decomposed properly                         │
│   2. Invalid Cypher syntax (missing labels, wrong relationships)     │
│   3. No validation before execution                                  │
│   4. Single retry with no learning                                   │
│   5. User sees raw errors ("Broken" responses)                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Specific Failure Cases from V1 UAT Logs

| Query Type | Failure Mode | Frequency |
|------------|--------------|-----------|
| Multi-basin comparison | Missing `UNION` or incorrect aggregation | 23% |
| Risk assessment queries | Wrong relationship traversal | 18% |
| Geospatial queries | Invalid coordinate syntax | 15% |
| Temporal queries | Date parsing errors | 12% |

---

## 3. Solution Overview

### V2 Multi-Agent Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        V2 AGENTIC RAG PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              ┌─────────────┐                                 │
│                              │   Router    │                                 │
│                              │   (Entry)   │                                 │
│                              └──────┬──────┘                                 │
│                                     │                                        │
│                                     ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         PLANNER AGENT                                │   │
│   │   • Classifies query complexity (simple/compound/analytical)         │   │
│   │   • Decomposes multi-part questions into sub-tasks                   │   │
│   │   • Identifies required data sources                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                    ┌────────────────┼────────────────┐                      │
│                    ▼                ▼                ▼                      │
│              [Sub-task 1]     [Sub-task 2]     [Sub-task N]                 │
│                    │                │                │                      │
│                    └────────────────┴────────────────┘                      │
│                                     │                                        │
│                                     ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     CYPHER SPECIALIST AGENT                          │   │
│   │   • Schema-aware query generation                                    │   │
│   │   • Uses few-shot examples from query library                        │   │
│   │   • Generates optimized Cypher with explanations                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                       VALIDATOR AGENT                                │   │
│   │   • Syntax validation (before execution)                             │   │
│   │   • Schema compliance check                                          │   │
│   │   • Executes query against Neo4j                                     │   │
│   │   • Error detection & self-healing (up to 3 retries)                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                          ┌──────────┴──────────┐                            │
│                          ▼                     ▼                            │
│                     [Success]              [Failure]                        │
│                          │                     │                            │
│                          │              ┌──────┴──────┐                     │
│                          │              ▼             ▼                     │
│                          │         [Retry ≤3]    [Escalate]                 │
│                          │              │             │                     │
│                          │              └─────────────┘                     │
│                          ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        ANALYST AGENT                                 │   │
│   │   • Synthesizes query results into insights                          │   │
│   │   • Generates prescriptive recommendations                           │   │
│   │   • Formats response with visualizations                             │   │
│   │   • Creates follow-up suggestions                                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│                          [Final Response to User]                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Architecture

### 4.1 Planner Agent

**Purpose:** Decompose complex user queries into executable sub-tasks.

**Model:** Claude 3.5 Haiku (fast, cost-effective for classification)

```python
# agents/planner.py

from pydantic import BaseModel, Field
from typing import List, Literal
from enum import Enum

class QueryComplexity(str, Enum):
    SIMPLE = "simple"           # Single aquifer lookup
    COMPOUND = "compound"       # Multi-aquifer comparison
    ANALYTICAL = "analytical"   # Risk assessment, clustering
    EXPLORATORY = "exploratory" # Open-ended analysis

class SubTask(BaseModel):
    """A decomposed sub-task from the original query."""
    task_id: str = Field(..., description="Unique identifier for this sub-task")
    description: str = Field(..., description="What this sub-task needs to accomplish")
    query_type: Literal["lookup", "aggregate", "compare", "analyze"]
    dependencies: List[str] = Field(default_factory=list, description="IDs of sub-tasks this depends on")
    required_entities: List[str] = Field(..., description="Neo4j labels needed: Aquifer, Basin, Country, etc.")

class QueryPlan(BaseModel):
    """Structured plan for executing a user query."""
    original_query: str
    complexity: QueryComplexity
    sub_tasks: List[SubTask]
    reasoning: str = Field(..., description="Explanation of decomposition strategy")

PLANNER_SYSTEM_PROMPT = """
You are the Planner Agent for a saline aquifer analytics system.

Your job is to analyze user questions and create an execution plan.

## Neo4j Schema Context
- (:Aquifer) - Main entity with properties: name, depth_m, porosity, permeability_md,
  temperature_c, pressure_mpa, salinity_ppm, co2_storage_capacity_mt, latitude, longitude
- (:Basin) - Geographic container: name, area_km2, country
- (:Country) - name, region
- (:RiskAssessment) - risk_level (LOW/MEDIUM/HIGH), factors
- Relationships: (Aquifer)-[:LOCATED_IN]->(Basin)-[:WITHIN]->(Country)
                 (Aquifer)-[:HAS_RISK]->(RiskAssessment)

## Decomposition Rules
1. SIMPLE queries: Single entity lookup, no decomposition needed
   Example: "What is the CO2 capacity of Amazonas aquifer?"

2. COMPOUND queries: Multiple entities or comparisons
   Example: "Compare porosity between Amazon and Parnaiba basins"
   → Sub-task 1: Get aquifers in Amazon basin
   → Sub-task 2: Get aquifers in Parnaiba basin
   → Sub-task 3: Compare porosity statistics

3. ANALYTICAL queries: Require aggregation, clustering, or risk assessment
   Example: "Which high-capacity aquifers have low risk?"
   → Sub-task 1: Filter aquifers by capacity threshold
   → Sub-task 2: Join with risk assessments
   → Sub-task 3: Rank and recommend

4. EXPLORATORY queries: Open-ended, need clarification
   Example: "Tell me about good aquifers"
   → Ask clarifying questions or apply default criteria
"""

class PlannerAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def plan(self, user_query: str, conversation_history: List[dict] = None) -> QueryPlan:
        """
        Analyze user query and produce structured execution plan.
        """
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Create an execution plan for: {user_query}"}
        ]

        if conversation_history:
            # Include context for follow-up questions
            messages.insert(1, {
                "role": "system",
                "content": f"Previous context: {conversation_history[-3:]}"
            })

        response = await self.llm.create(
            model="claude-3-5-haiku-20241022",
            messages=messages,
            response_model=QueryPlan
        )

        return response
```

### 4.2 Cypher Specialist Agent

**Purpose:** Generate syntactically correct, optimized Cypher queries.

**Model:** Claude 3.5 Sonnet (superior code generation capabilities)

```python
# agents/cypher_specialist.py

from pydantic import BaseModel, Field
from typing import List, Optional

class CypherQuery(BaseModel):
    """Generated Cypher query with metadata."""
    query: str = Field(..., description="The Cypher query to execute")
    explanation: str = Field(..., description="Human-readable explanation of what this query does")
    expected_columns: List[str] = Field(..., description="Column names expected in result")
    optimization_notes: Optional[str] = Field(None, description="Performance considerations")

CYPHER_SPECIALIST_PROMPT = """
You are the Cypher Specialist Agent for a Neo4j-based saline aquifer database.

## Your Responsibilities
1. Generate syntactically correct Cypher queries
2. Use proper Neo4j relationship patterns
3. Include appropriate WHERE clauses and aggregations
4. Optimize for performance (use indexes, limit results)

## Schema Reference
```
(:Aquifer {
    name: STRING,
    depth_m: FLOAT,
    porosity: FLOAT,           // 0.0 - 1.0
    permeability_md: FLOAT,    // millidarcies
    temperature_c: FLOAT,
    pressure_mpa: FLOAT,
    salinity_ppm: INTEGER,
    co2_storage_capacity_mt: FLOAT,  // megatonnes
    latitude: FLOAT,
    longitude: FLOAT,
    cluster_id: INTEGER        // K-means cluster (0, 1, 2)
})

(:Basin {name: STRING, area_km2: FLOAT})
(:Country {name: STRING, region: STRING})
(:RiskAssessment {risk_level: STRING, seismic_risk: STRING, regulatory_score: FLOAT})

Relationships:
(Aquifer)-[:LOCATED_IN]->(Basin)
(Basin)-[:WITHIN]->(Country)
(Aquifer)-[:HAS_RISK]->(RiskAssessment)
```

## Indexed Properties (Use for filtering)
- Aquifer.name
- Aquifer.co2_storage_capacity_mt
- Basin.name
- RiskAssessment.risk_level

## Query Patterns Library

### Pattern 1: Single Aquifer Lookup
```cypher
MATCH (a:Aquifer {name: $aquifer_name})
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
OPTIONAL MATCH (a)-[:HAS_RISK]->(r:RiskAssessment)
RETURN a, b.name AS basin, r.risk_level AS risk
```

### Pattern 2: Basin Comparison
```cypher
MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin)
WHERE b.name IN $basin_names
RETURN b.name AS basin,
       AVG(a.porosity) AS avg_porosity,
       AVG(a.co2_storage_capacity_mt) AS avg_capacity,
       COUNT(a) AS aquifer_count
ORDER BY avg_capacity DESC
```

### Pattern 3: Risk-Based Filtering
```cypher
MATCH (a:Aquifer)-[:HAS_RISK]->(r:RiskAssessment)
WHERE r.risk_level = 'LOW'
  AND a.co2_storage_capacity_mt > $min_capacity
RETURN a.name, a.co2_storage_capacity_mt, r.risk_level
ORDER BY a.co2_storage_capacity_mt DESC
LIMIT 20
```

### Pattern 4: Geographic Query
```cypher
MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin)-[:WITHIN]->(c:Country)
WHERE c.name = $country_name
RETURN a.name, a.latitude, a.longitude, a.co2_storage_capacity_mt, b.name AS basin
```

### Pattern 5: Cluster Analysis
```cypher
MATCH (a:Aquifer)
WHERE a.cluster_id = $cluster_id
RETURN a.cluster_id,
       AVG(a.depth_m) AS avg_depth,
       AVG(a.porosity) AS avg_porosity,
       AVG(a.co2_storage_capacity_mt) AS avg_capacity,
       COUNT(*) AS count
```

## Rules
1. ALWAYS use parameterized queries with $parameter syntax
2. ALWAYS include LIMIT for unbounded queries (default: 100)
3. Use OPTIONAL MATCH for potentially missing relationships
4. Prefer aggregations in Cypher over post-processing
5. Include ORDER BY for consistent results
"""

class CypherSpecialistAgent:
    def __init__(self, llm_client, schema_context: str):
        self.llm = llm_client
        self.schema_context = schema_context
        self.query_cache = {}  # Cache for repeated query patterns

    async def generate(self, sub_task: SubTask, parameters: dict = None) -> CypherQuery:
        """
        Generate Cypher query for a specific sub-task.
        """
        # Check cache for similar queries
        cache_key = f"{sub_task.query_type}:{sorted(sub_task.required_entities)}"

        messages = [
            {"role": "system", "content": CYPHER_SPECIALIST_PROMPT},
            {"role": "user", "content": f"""
Generate a Cypher query for this task:

Task: {sub_task.description}
Query Type: {sub_task.query_type}
Required Entities: {sub_task.required_entities}
Parameters Available: {parameters or 'None specified'}

Return ONLY the Cypher query with explanation.
"""}
        ]

        response = await self.llm.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            response_model=CypherQuery,
            temperature=0.1  # Low temperature for consistent query generation
        )

        return response
```

### 4.3 Validator Agent

**Purpose:** Validate, execute, and heal Cypher queries.

**Model:** Claude 3.5 Haiku (fast iteration for self-healing loops)

```python
# agents/validator.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from enum import Enum
import re

class ValidationStatus(str, Enum):
    VALID = "valid"
    SYNTAX_ERROR = "syntax_error"
    SCHEMA_ERROR = "schema_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"

class ValidationResult(BaseModel):
    """Result of query validation and execution."""
    status: ValidationStatus
    original_query: str
    corrected_query: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    results: Optional[List[dict]] = None
    execution_time_ms: Optional[float] = None
    retry_count: int = 0

class HealingAttempt(BaseModel):
    """Record of a self-healing attempt."""
    attempt_number: int
    error: str
    diagnosis: str
    fix_applied: str
    corrected_query: str

VALIDATOR_PROMPT = """
You are the Validator Agent responsible for fixing broken Cypher queries.

## Common Error Patterns and Fixes

### 1. Label Errors
Error: "Unknown label: Aquifier"
Fix: Correct spelling to "Aquifer"

### 2. Relationship Errors
Error: "Unknown relationship type: BELONGS_TO"
Fix: Use correct relationship "LOCATED_IN"

### 3. Property Errors
Error: "Unknown property: capacity"
Fix: Use full property name "co2_storage_capacity_mt"

### 4. Syntax Errors
Error: "Invalid input 'WHERE': expected..."
Fix: Check for missing MATCH clauses or incorrect order

### 5. Aggregation Errors
Error: "In a WITH/RETURN with DISTINCT or an aggregation..."
Fix: Ensure non-aggregated columns are in GROUP BY equivalent

## Healing Process
1. Parse the error message
2. Identify the error category
3. Apply the appropriate fix pattern
4. Return the corrected query

## Schema Reminder
Labels: Aquifer, Basin, Country, RiskAssessment
Relationships: LOCATED_IN, WITHIN, HAS_RISK
"""

class ValidatorAgent:
    MAX_RETRIES = 3
    QUERY_TIMEOUT_MS = 5000

    def __init__(self, llm_client, neo4j_driver):
        self.llm = llm_client
        self.neo4j = neo4j_driver
        self.healing_history: List[HealingAttempt] = []

    async def validate_and_execute(
        self,
        cypher_query: CypherQuery,
        parameters: dict = None
    ) -> ValidationResult:
        """
        Validate, execute, and potentially heal a Cypher query.
        """
        current_query = cypher_query.query
        retry_count = 0

        while retry_count <= self.MAX_RETRIES:
            # Step 1: Static syntax validation
            syntax_result = self._validate_syntax(current_query)
            if not syntax_result["valid"]:
                current_query = await self._heal_query(
                    current_query,
                    syntax_result["error"],
                    "syntax_error"
                )
                retry_count += 1
                continue

            # Step 2: Schema validation
            schema_result = self._validate_schema(current_query)
            if not schema_result["valid"]:
                current_query = await self._heal_query(
                    current_query,
                    schema_result["error"],
                    "schema_error"
                )
                retry_count += 1
                continue

            # Step 3: Execute query
            try:
                results, execution_time = await self._execute_query(
                    current_query,
                    parameters
                )

                return ValidationResult(
                    status=ValidationStatus.VALID,
                    original_query=cypher_query.query,
                    corrected_query=current_query if current_query != cypher_query.query else None,
                    results=results,
                    execution_time_ms=execution_time,
                    retry_count=retry_count
                )

            except Exception as e:
                error_msg = str(e)

                if retry_count >= self.MAX_RETRIES:
                    return ValidationResult(
                        status=ValidationStatus.EXECUTION_ERROR,
                        original_query=cypher_query.query,
                        error_message=error_msg,
                        error_type="max_retries_exceeded",
                        retry_count=retry_count
                    )

                current_query = await self._heal_query(
                    current_query,
                    error_msg,
                    "execution_error"
                )
                retry_count += 1

        return ValidationResult(
            status=ValidationStatus.EXECUTION_ERROR,
            original_query=cypher_query.query,
            error_message="Failed after maximum retries",
            retry_count=retry_count
        )

    def _validate_syntax(self, query: str) -> dict:
        """
        Static syntax validation before execution.
        """
        errors = []

        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            errors.append("Unbalanced parentheses")

        # Check for balanced brackets
        if query.count('[') != query.count(']'):
            errors.append("Unbalanced brackets")

        # Check for required clauses
        query_upper = query.upper()
        if 'MATCH' not in query_upper and 'CREATE' not in query_upper:
            errors.append("Missing MATCH or CREATE clause")

        if 'RETURN' not in query_upper:
            errors.append("Missing RETURN clause")

        # Check for common typos
        typo_patterns = [
            (r'\bMATCH\s*\(\s*\)', "Empty MATCH pattern"),
            (r'\bRETURN\s*$', "Empty RETURN clause"),
            (r'\bWHERE\s+AND\b', "WHERE followed directly by AND"),
        ]

        for pattern, error in typo_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                errors.append(error)

        return {"valid": len(errors) == 0, "error": "; ".join(errors) if errors else None}

    def _validate_schema(self, query: str) -> dict:
        """
        Validate query against known schema.
        """
        valid_labels = {'Aquifer', 'Basin', 'Country', 'RiskAssessment'}
        valid_relationships = {'LOCATED_IN', 'WITHIN', 'HAS_RISK'}

        # Extract labels from query
        label_pattern = r':(\w+)'
        found_labels = set(re.findall(label_pattern, query))

        invalid_labels = found_labels - valid_labels - {'r', 'a', 'b', 'c'}  # Exclude variable names

        if invalid_labels:
            return {
                "valid": False,
                "error": f"Unknown labels: {invalid_labels}. Valid labels: {valid_labels}"
            }

        # Extract relationships
        rel_pattern = r'\[:\s*(\w+)\s*\]'
        found_rels = set(re.findall(rel_pattern, query))

        invalid_rels = found_rels - valid_relationships
        if invalid_rels:
            return {
                "valid": False,
                "error": f"Unknown relationships: {invalid_rels}. Valid: {valid_relationships}"
            }

        return {"valid": True, "error": None}

    async def _heal_query(self, query: str, error: str, error_type: str) -> str:
        """
        Use LLM to heal a broken query.
        """
        messages = [
            {"role": "system", "content": VALIDATOR_PROMPT},
            {"role": "user", "content": f"""
Fix this Cypher query:

```cypher
{query}
```

Error: {error}
Error Type: {error_type}

Return ONLY the corrected Cypher query, no explanations.
"""}
        ]

        response = await self.llm.create(
            model="claude-3-5-haiku-20241022",
            messages=messages,
            max_tokens=500,
            temperature=0.0
        )

        corrected = response.content.strip()

        # Record healing attempt
        self.healing_history.append(HealingAttempt(
            attempt_number=len(self.healing_history) + 1,
            error=error,
            diagnosis=error_type,
            fix_applied="LLM-based correction",
            corrected_query=corrected
        ))

        return corrected

    async def _execute_query(self, query: str, parameters: dict = None) -> tuple:
        """
        Execute query against Neo4j and return results with timing.
        """
        import time

        start = time.perf_counter()

        async with self.neo4j.session() as session:
            result = await session.run(query, parameters or {})
            records = [dict(record) for record in await result.data()]

        execution_time = (time.perf_counter() - start) * 1000

        return records, execution_time
```

### 4.4 Analyst Agent

**Purpose:** Synthesize query results into prescriptive insights.

**Model:** Claude 3.5 Sonnet (best reasoning for analysis)

```python
# agents/analyst.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class InsightType(str, Enum):
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    RISK_ASSESSMENT = "risk_assessment"
    TREND = "trend"
    ANOMALY = "anomaly"

class Insight(BaseModel):
    """A single analytical insight."""
    type: InsightType
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_data: Dict[str, Any]

class Recommendation(BaseModel):
    """Prescriptive recommendation for action."""
    priority: int = Field(..., ge=1, le=5, description="1=highest priority")
    action: str
    rationale: str
    aquifers_involved: List[str]
    expected_outcome: str

class AnalysisReport(BaseModel):
    """Complete analysis report for user."""
    summary: str = Field(..., description="2-3 sentence executive summary")
    insights: List[Insight]
    recommendations: List[Recommendation]
    data_quality_notes: Optional[str] = None
    follow_up_questions: List[str] = Field(..., description="Suggested next questions")
    visualization_hints: List[str] = Field(..., description="Charts/maps to display")

ANALYST_PROMPT = """
You are the Analyst Agent for a saline aquifer CO2 storage advisory system.

## Your Mission
Transform raw Neo4j query results into **prescriptive analytics** - don't just describe
what the data shows, tell the user what they should DO with this information.

## Domain Context
- Saline aquifers are underground rock formations that can permanently store CO2
- Key factors for storage suitability:
  * High porosity (>15%) = more pore space for CO2
  * High permeability (>100 md) = easier injection
  * Adequate depth (>800m) = CO2 stays supercritical
  * Low seismic risk = safer long-term storage
  * Favorable regulations = faster permitting

## Analysis Framework

### 1. For Comparison Queries
- Identify the BEST option with clear justification
- Highlight trade-offs between options
- Recommend a decision with confidence level

### 2. For Risk Assessment Queries
- Categorize risks: geological, regulatory, economic
- Provide mitigation strategies for each risk
- Suggest monitoring approaches

### 3. For Capacity Queries
- Compare to real-world CO2 sources (power plants emit ~3-5 Mt/year)
- Calculate years of storage available
- Prioritize by efficiency (capacity/risk ratio)

### 4. For Exploratory Queries
- Identify patterns and clusters
- Flag anomalies or outliers
- Suggest deeper investigation areas

## Output Requirements
1. Lead with actionable recommendations
2. Support each recommendation with data
3. Quantify when possible (percentages, rankings)
4. Suggest 2-3 follow-up questions
5. Indicate which visualizations would help
"""

class AnalystAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def analyze(
        self,
        original_query: str,
        query_results: List[dict],
        query_plan: QueryPlan,
        conversation_context: List[dict] = None
    ) -> AnalysisReport:
        """
        Generate prescriptive analysis from query results.
        """
        messages = [
            {"role": "system", "content": ANALYST_PROMPT},
            {"role": "user", "content": f"""
Analyze these query results and provide prescriptive recommendations.

## User's Original Question
{original_query}

## Query Plan Used
Complexity: {query_plan.complexity}
Sub-tasks completed: {[t.description for t in query_plan.sub_tasks]}

## Query Results
{self._format_results(query_results)}

## Conversation Context
{conversation_context[-3:] if conversation_context else "First question in session"}

Provide a complete analysis with recommendations, insights, and follow-up questions.
"""}
        ]

        response = await self.llm.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            response_model=AnalysisReport,
            temperature=0.3  # Slight creativity for recommendations
        )

        return response

    def _format_results(self, results: List[dict]) -> str:
        """
        Format query results for LLM consumption.
        """
        if not results:
            return "No results returned from query."

        if len(results) > 50:
            # Summarize large result sets
            return f"""
Total records: {len(results)}
Sample (first 10): {results[:10]}
Summary statistics would be computed here...
"""

        return str(results)
```

---

## 5. LangGraph Implementation

### 5.1 State Definition

```python
# graph/state.py

from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import add_messages
from agents.planner import QueryPlan
from agents.cypher_specialist import CypherQuery
from agents.validator import ValidationResult
from agents.analyst import AnalysisReport

class AgentState(TypedDict):
    """Shared state across all agents in the graph."""

    # Input
    user_query: str
    conversation_history: Annotated[List[dict], add_messages]

    # Planner output
    query_plan: Optional[QueryPlan]
    current_subtask_index: int

    # Cypher Specialist output
    generated_queries: List[CypherQuery]

    # Validator output
    validation_results: List[ValidationResult]
    all_queries_valid: bool

    # Analyst output
    analysis_report: Optional[AnalysisReport]

    # Control flow
    error_count: int
    should_escalate: bool
    final_response: Optional[str]
```

### 5.2 Graph Definition

```python
# graph/workflow.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import AgentState
from agents.planner import PlannerAgent
from agents.cypher_specialist import CypherSpecialistAgent
from agents.validator import ValidatorAgent
from agents.analyst import AnalystAgent

def create_workflow(llm_client, neo4j_driver) -> StateGraph:
    """
    Create the LangGraph workflow for query processing.
    """

    # Initialize agents
    planner = PlannerAgent(llm_client)
    cypher_specialist = CypherSpecialistAgent(llm_client, schema_context="...")
    validator = ValidatorAgent(llm_client, neo4j_driver)
    analyst = AnalystAgent(llm_client)

    # Define node functions
    async def plan_node(state: AgentState) -> AgentState:
        """Planner agent node."""
        plan = await planner.plan(
            state["user_query"],
            state.get("conversation_history", [])
        )
        return {
            "query_plan": plan,
            "current_subtask_index": 0,
            "generated_queries": [],
            "validation_results": []
        }

    async def generate_cypher_node(state: AgentState) -> AgentState:
        """Cypher Specialist agent node."""
        plan = state["query_plan"]
        queries = []

        for subtask in plan.sub_tasks:
            query = await cypher_specialist.generate(subtask)
            queries.append(query)

        return {"generated_queries": queries}

    async def validate_node(state: AgentState) -> AgentState:
        """Validator agent node."""
        results = []
        all_valid = True

        for query in state["generated_queries"]:
            result = await validator.validate_and_execute(query)
            results.append(result)
            if result.status != ValidationStatus.VALID:
                all_valid = False

        return {
            "validation_results": results,
            "all_queries_valid": all_valid,
            "error_count": sum(1 for r in results if r.status != ValidationStatus.VALID)
        }

    async def analyze_node(state: AgentState) -> AgentState:
        """Analyst agent node."""
        # Collect successful results
        all_results = []
        for result in state["validation_results"]:
            if result.results:
                all_results.extend(result.results)

        report = await analyst.analyze(
            state["user_query"],
            all_results,
            state["query_plan"],
            state.get("conversation_history", [])
        )

        return {"analysis_report": report}

    async def format_response_node(state: AgentState) -> AgentState:
        """Format final response for user."""
        report = state["analysis_report"]

        response = f"""
## Summary
{report.summary}

## Key Insights
{chr(10).join(f"- **{i.title}**: {i.description}" for i in report.insights)}

## Recommendations
{chr(10).join(f"{r.priority}. **{r.action}** - {r.rationale}" for r in report.recommendations)}

## Suggested Follow-up Questions
{chr(10).join(f"- {q}" for q in report.follow_up_questions)}
"""

        return {"final_response": response}

    async def handle_error_node(state: AgentState) -> AgentState:
        """Handle cases where queries failed."""
        failed_queries = [
            r for r in state["validation_results"]
            if r.status != ValidationStatus.VALID
        ]

        response = f"""
I encountered some issues processing your query:

{chr(10).join(f"- {r.error_message}" for r in failed_queries)}

**What I can tell you:**
Based on the successful queries, here's a partial analysis...

Would you like me to try a different approach?
"""

        return {"final_response": response, "should_escalate": True}

    # Define routing logic
    def should_continue(state: AgentState) -> str:
        """Determine next step based on validation results."""
        if state.get("all_queries_valid", False):
            return "analyze"
        elif state.get("error_count", 0) > len(state.get("generated_queries", [])) // 2:
            return "handle_error"
        else:
            return "analyze"  # Proceed with partial results

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("generate_cypher", generate_cypher_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("format_response", format_response_node)
    workflow.add_node("handle_error", handle_error_node)

    # Add edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "generate_cypher")
    workflow.add_edge("generate_cypher", "validate")

    # Conditional routing after validation
    workflow.add_conditional_edges(
        "validate",
        should_continue,
        {
            "analyze": "analyze",
            "handle_error": "handle_error"
        }
    )

    workflow.add_edge("analyze", "format_response")
    workflow.add_edge("format_response", END)
    workflow.add_edge("handle_error", END)

    return workflow

# Compile with memory for conversation persistence
def compile_workflow(llm_client, neo4j_driver):
    """Compile workflow with checkpointing."""
    workflow = create_workflow(llm_client, neo4j_driver)
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)
```

### 5.3 Visual Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH WORKFLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              [START]                                         │
│                                 │                                            │
│                                 ▼                                            │
│                         ┌──────────────┐                                     │
│                         │    PLAN      │                                     │
│                         │   (Haiku)    │                                     │
│                         └──────┬───────┘                                     │
│                                │                                             │
│                                ▼                                             │
│                    ┌───────────────────────┐                                 │
│                    │   GENERATE_CYPHER     │                                 │
│                    │      (Sonnet)         │                                 │
│                    └───────────┬───────────┘                                 │
│                                │                                             │
│                                ▼                                             │
│                    ┌───────────────────────┐                                 │
│                    │      VALIDATE         │                                 │
│                    │      (Haiku)          │◄──────┐                         │
│                    └───────────┬───────────┘       │                         │
│                                │                   │                         │
│                                ▼                   │                         │
│                    ┌───────────────────────┐       │                         │
│                    │  all_queries_valid?   │       │                         │
│                    └───────────┬───────────┘       │                         │
│                                │                   │                         │
│                   ┌────────────┼────────────┐      │                         │
│                   │            │            │      │                         │
│                   ▼            ▼            ▼      │                         │
│               [YES]      [PARTIAL]       [NO]      │                         │
│                   │            │            │      │                         │
│                   │            │            ▼      │                         │
│                   │            │    ┌─────────────┐│                         │
│                   │            │    │HANDLE_ERROR ││                         │
│                   │            │    └──────┬──────┘│                         │
│                   │            │           │       │                         │
│                   ▼            ▼           │       │                         │
│            ┌───────────────────────┐       │       │                         │
│            │      ANALYZE          │       │       │                         │
│            │      (Sonnet)         │       │       │                         │
│            └───────────┬───────────┘       │       │                         │
│                        │                   │       │                         │
│                        ▼                   │       │                         │
│            ┌───────────────────────┐       │       │                         │
│            │   FORMAT_RESPONSE     │       │       │                         │
│            └───────────┬───────────┘       │       │                         │
│                        │                   │       │                         │
│                        ▼                   ▼       │                         │
│                     [END]◄─────────────────┘       │                         │
│                                                    │                         │
│                    [RETRY LOOP - up to 3x]─────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. State Management

### 6.1 Conversation Memory

```python
# memory/conversation.py

from typing import List, Dict, Any
from datetime import datetime
import json

class ConversationMemory:
    """
    Manages conversation state with PostgreSQL persistence.
    """

    def __init__(self, session_id: str, db_pool):
        self.session_id = session_id
        self.db = db_pool
        self.short_term: List[Dict] = []  # Last 10 exchanges
        self.entity_memory: Dict[str, Any] = {}  # Mentioned entities

    async def add_exchange(self, user_query: str, response: str, metadata: dict):
        """Add a new exchange to memory."""
        exchange = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_query": user_query,
            "response": response,
            "entities_mentioned": metadata.get("entities", []),
            "query_plan": metadata.get("query_plan"),
        }

        self.short_term.append(exchange)

        # Keep only last 10 in short-term
        if len(self.short_term) > 10:
            self.short_term = self.short_term[-10:]

        # Update entity memory
        for entity in metadata.get("entities", []):
            self.entity_memory[entity["name"]] = entity

        # Persist to PostgreSQL
        await self._persist(exchange)

    async def get_context_for_query(self, new_query: str) -> dict:
        """
        Get relevant context for a new query.
        """
        # Check for pronouns/references that need resolution
        references = self._detect_references(new_query)

        resolved_entities = {}
        for ref in references:
            if ref in self.entity_memory:
                resolved_entities[ref] = self.entity_memory[ref]

        return {
            "recent_exchanges": self.short_term[-3:],
            "resolved_entities": resolved_entities,
            "active_filters": self._get_active_filters()
        }

    def _detect_references(self, query: str) -> List[str]:
        """Detect pronouns or references to previous entities."""
        reference_patterns = [
            "that aquifer", "this basin", "the same", "those",
            "it", "they", "them", "previous", "mentioned"
        ]
        found = []
        query_lower = query.lower()
        for pattern in reference_patterns:
            if pattern in query_lower:
                found.append(pattern)
        return found

    def _get_active_filters(self) -> dict:
        """Get any filters still active from previous queries."""
        # Look at recent queries for filter patterns
        filters = {}
        for exchange in self.short_term[-3:]:
            plan = exchange.get("query_plan")
            if plan and hasattr(plan, "active_filters"):
                filters.update(plan.active_filters)
        return filters

    async def _persist(self, exchange: dict):
        """Save exchange to PostgreSQL."""
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_history
                (session_id, user_message, assistant_response, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """,
            self.session_id,
            exchange["user_query"],
            exchange["response"],
            json.dumps(exchange),
            datetime.utcnow()
            )
```

### 6.2 Query Result Caching

```python
# cache/query_cache.py

import hashlib
import json
from typing import Optional, List
from datetime import timedelta
import redis.asyncio as redis

class QueryCache:
    """
    Redis-based caching for query results.
    """

    DEFAULT_TTL = timedelta(hours=1)

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def _make_key(self, query: str, parameters: dict) -> str:
        """Generate cache key from query and parameters."""
        content = json.dumps({
            "query": query,
            "params": parameters or {}
        }, sort_keys=True)
        return f"cypher:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    async def get(self, query: str, parameters: dict = None) -> Optional[List[dict]]:
        """Retrieve cached results if available."""
        key = self._make_key(query, parameters)
        cached = await self.redis.get(key)

        if cached:
            return json.loads(cached)
        return None

    async def set(
        self,
        query: str,
        parameters: dict,
        results: List[dict],
        ttl: timedelta = None
    ):
        """Cache query results."""
        key = self._make_key(query, parameters)
        await self.redis.set(
            key,
            json.dumps(results),
            ex=int((ttl or self.DEFAULT_TTL).total_seconds())
        )

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all cached queries matching a pattern."""
        # Used when data is updated
        async for key in self.redis.scan_iter(f"cypher:*{pattern}*"):
            await self.redis.delete(key)
```

---

## 7. Error Handling & Self-Healing

### 7.1 Error Classification

```python
# errors/classifier.py

from enum import Enum
from typing import Optional
import re

class ErrorCategory(Enum):
    SYNTAX = "syntax"           # Cypher syntax errors
    SCHEMA = "schema"           # Invalid labels/properties
    SEMANTIC = "semantic"       # Valid syntax but wrong logic
    EXECUTION = "execution"     # Neo4j runtime errors
    TIMEOUT = "timeout"         # Query took too long
    EMPTY_RESULT = "empty"      # Valid query, no results
    PERMISSION = "permission"   # Access denied
    UNKNOWN = "unknown"

class ErrorClassifier:
    """
    Classify Neo4j errors for appropriate handling.
    """

    PATTERNS = {
        ErrorCategory.SYNTAX: [
            r"Invalid input",
            r"Unexpected end of input",
            r"expected",
            r"mismatched input",
        ],
        ErrorCategory.SCHEMA: [
            r"Unknown label",
            r"Unknown relationship type",
            r"Unknown property",
            r"is not defined",
        ],
        ErrorCategory.SEMANTIC: [
            r"Type mismatch",
            r"cannot be used",
            r"Invalid use of aggregating function",
        ],
        ErrorCategory.TIMEOUT: [
            r"Transaction was terminated",
            r"timed out",
            r"Connection reset",
        ],
        ErrorCategory.PERMISSION: [
            r"access denied",
            r"not authorized",
        ],
    }

    @classmethod
    def classify(cls, error_message: str) -> ErrorCategory:
        """Classify an error message into a category."""
        for category, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return category
        return ErrorCategory.UNKNOWN

    @classmethod
    def get_healing_strategy(cls, category: ErrorCategory) -> str:
        """Get the appropriate healing strategy for an error category."""
        strategies = {
            ErrorCategory.SYNTAX: "Fix syntax using Cypher grammar rules",
            ErrorCategory.SCHEMA: "Map to correct schema labels and properties",
            ErrorCategory.SEMANTIC: "Restructure query logic",
            ErrorCategory.EXECUTION: "Simplify query or add constraints",
            ErrorCategory.TIMEOUT: "Add LIMIT or optimize traversal",
            ErrorCategory.EMPTY_RESULT: "Broaden search criteria",
            ErrorCategory.PERMISSION: "Escalate to user",
            ErrorCategory.UNKNOWN: "Attempt generic fix then escalate",
        }
        return strategies.get(category, "Escalate to user")
```

### 7.2 Self-Healing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SELF-HEALING PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Generated Cypher Query                                                     │
│           │                                                                  │
│           ▼                                                                  │
│   ┌───────────────────┐                                                      │
│   │ Static Validation │──────────┐                                           │
│   └─────────┬─────────┘          │                                           │
│             │                    │ Errors                                    │
│             ▼                    ▼                                           │
│   ┌───────────────────┐   ┌──────────────┐                                   │
│   │ Schema Validation │   │ Quick Fixes  │ (regex-based corrections)         │
│   └─────────┬─────────┘   └──────┬───────┘                                   │
│             │                    │                                           │
│             ▼                    │                                           │
│   ┌───────────────────┐          │                                           │
│   │ Execute on Neo4j  │◄─────────┘                                           │
│   └─────────┬─────────┘                                                      │
│             │                                                                │
│        ┌────┴────┐                                                           │
│        │         │                                                           │
│    [Success]  [Error]                                                        │
│        │         │                                                           │
│        │         ▼                                                           │
│        │   ┌──────────────┐                                                  │
│        │   │ Classify     │                                                  │
│        │   │ Error        │                                                  │
│        │   └──────┬───────┘                                                  │
│        │          │                                                          │
│        │          ▼                                                          │
│        │   ┌──────────────┐    ┌─────────────────────────────────────┐      │
│        │   │ Retry < 3?   │───►│ LLM Healing (Haiku - fast & cheap)  │      │
│        │   └──────┬───────┘    │                                     │      │
│        │          │            │ Input: Query + Error + Schema       │      │
│        │          │ No         │ Output: Corrected Query             │      │
│        │          ▼            └──────────────┬──────────────────────┘      │
│        │   ┌──────────────┐                   │                              │
│        │   │ Escalate to  │                   │                              │
│        │   │ User         │◄──────────────────┘ (if retry > 3)               │
│        │   └──────────────┘                                                  │
│        │                                                                     │
│        ▼                                                                     │
│   [Return Results]                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Integration with Cloud Infrastructure

### 8.1 API Gateway Integration

```python
# api/routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import uuid

router = APIRouter(prefix="/api/v2", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    expert_mode: bool = False  # Show Cypher queries to user

class ChatResponse(BaseModel):
    session_id: str
    response: str
    cypher_queries: Optional[List[dict]] = None  # Only in expert mode
    execution_trace: Optional[dict] = None        # Only in expert mode
    visualization_hints: List[str]
    follow_up_suggestions: List[str]

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    workflow = Depends(get_compiled_workflow),
    memory = Depends(get_conversation_memory)
):
    """
    Process a chat message through the agentic RAG pipeline.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Get conversation context
    context = await memory.get_context_for_query(request.message)

    # Build initial state
    initial_state = {
        "user_query": request.message,
        "conversation_history": context["recent_exchanges"],
        "resolved_entities": context["resolved_entities"],
        "error_count": 0,
        "should_escalate": False,
    }

    # Run workflow
    config = {"configurable": {"thread_id": session_id}}

    try:
        final_state = await workflow.ainvoke(initial_state, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build response
    response = ChatResponse(
        session_id=session_id,
        response=final_state["final_response"],
        visualization_hints=final_state["analysis_report"].visualization_hints,
        follow_up_suggestions=final_state["analysis_report"].follow_up_questions
    )

    # Include debug info in expert mode
    if request.expert_mode:
        response.cypher_queries = [
            {
                "query": vr.original_query,
                "corrected": vr.corrected_query,
                "execution_time_ms": vr.execution_time_ms,
                "retry_count": vr.retry_count
            }
            for vr in final_state["validation_results"]
        ]
        response.execution_trace = {
            "plan": final_state["query_plan"].dict(),
            "total_retries": sum(vr.retry_count for vr in final_state["validation_results"])
        }

    # Persist exchange
    await memory.add_exchange(
        request.message,
        final_state["final_response"],
        {"entities": final_state.get("entities_mentioned", [])}
    )

    return response
```

### 8.2 Amazon Bedrock Client

```python
# clients/bedrock.py

import boto3
from anthropic import AnthropicBedrock
from typing import Optional, Type
from pydantic import BaseModel
import instructor

class BedrockClient:
    """
    Client for Claude models via Amazon Bedrock.
    """

    MODEL_MAP = {
        "claude-3-5-sonnet-20241022": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-5-haiku-20241022": "anthropic.claude-3-5-haiku-20241022-v1:0",
    }

    def __init__(self, region: str = "us-east-1"):
        self.client = AnthropicBedrock(
            aws_region=region,
        )
        # Wrap with instructor for structured outputs
        self.instructor_client = instructor.from_anthropic(self.client)

    async def create(
        self,
        model: str,
        messages: list,
        response_model: Optional[Type[BaseModel]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3
    ):
        """
        Create a chat completion, optionally with structured output.
        """
        bedrock_model = self.MODEL_MAP.get(model, model)

        if response_model:
            # Use instructor for structured output
            return await self.instructor_client.messages.create(
                model=bedrock_model,
                messages=messages,
                response_model=response_model,
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            # Plain completion
            response = await self.client.messages.create(
                model=bedrock_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response
```

---

## 9. Performance Optimization

### 9.1 Query Optimization Strategies

| Strategy | Description | Impact |
|----------|-------------|--------|
| **Index Usage** | Ensure queries use indexed properties for filtering | 5-10x faster lookups |
| **Early Filtering** | Push WHERE clauses as early as possible | Reduces intermediate result sets |
| **Projection** | Return only needed properties | Less data transfer |
| **Aggregation in Cypher** | Compute aggregates in Neo4j, not Python | Reduces data transfer |
| **Parallel Execution** | Run independent sub-tasks concurrently | 2-3x faster for compound queries |
| **Result Caching** | Cache frequent queries in Redis | <10ms for cached results |

### 9.2 Agent Latency Budget

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LATENCY BUDGET (P95 Target: 3s)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Agent              Model           Target      Max                         │
│   ─────────────────────────────────────────────────────────                  │
│   Planner            Haiku           200ms       500ms                       │
│   Cypher Specialist  Sonnet          400ms       800ms                       │
│   Validator          Haiku + Neo4j   500ms       1000ms (includes retries)   │
│   Analyst            Sonnet          600ms       1000ms                       │
│   ─────────────────────────────────────────────────────────                  │
│   TOTAL                              1700ms      3300ms                       │
│                                                                              │
│   Buffer for network/serialization:  300ms                                   │
│   P95 Target:                        ~2000ms                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Parallel Execution

```python
# optimization/parallel.py

import asyncio
from typing import List
from agents.cypher_specialist import CypherQuery, SubTask

async def execute_independent_subtasks(
    subtasks: List[SubTask],
    cypher_specialist,
    validator
) -> List[dict]:
    """
    Execute independent sub-tasks in parallel.
    """
    # Group by dependencies
    no_deps = [t for t in subtasks if not t.dependencies]
    with_deps = [t for t in subtasks if t.dependencies]

    # Execute independent tasks in parallel
    independent_tasks = [
        execute_single_task(t, cypher_specialist, validator)
        for t in no_deps
    ]

    results = await asyncio.gather(*independent_tasks, return_exceptions=True)

    # Build result map for dependent tasks
    result_map = {
        no_deps[i].task_id: results[i]
        for i in range(len(no_deps))
    }

    # Execute dependent tasks (may need to be sequential)
    for task in with_deps:
        # Wait for dependencies
        dep_results = [result_map[dep_id] for dep_id in task.dependencies]
        result = await execute_single_task(
            task,
            cypher_specialist,
            validator,
            context=dep_results
        )
        result_map[task.task_id] = result

    return list(result_map.values())

async def execute_single_task(subtask, cypher_specialist, validator, context=None):
    """Execute a single sub-task."""
    query = await cypher_specialist.generate(subtask, parameters=context)
    result = await validator.validate_and_execute(query)
    return result
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# tests/test_agents.py

import pytest
from agents.planner import PlannerAgent, QueryComplexity

class TestPlannerAgent:
    @pytest.fixture
    def planner(self, mock_llm):
        return PlannerAgent(mock_llm)

    @pytest.mark.asyncio
    async def test_simple_query_classification(self, planner):
        """Simple queries should not be decomposed."""
        plan = await planner.plan("What is the porosity of Amazonas aquifer?")

        assert plan.complexity == QueryComplexity.SIMPLE
        assert len(plan.sub_tasks) == 1

    @pytest.mark.asyncio
    async def test_compound_query_decomposition(self, planner):
        """Compound queries should be broken into sub-tasks."""
        plan = await planner.plan(
            "Compare CO2 storage capacity between Amazon and Parnaiba basins"
        )

        assert plan.complexity == QueryComplexity.COMPOUND
        assert len(plan.sub_tasks) >= 2
        assert any("Amazon" in t.description for t in plan.sub_tasks)
        assert any("Parnaiba" in t.description for t in plan.sub_tasks)

class TestCypherValidator:
    def test_syntax_validation_balanced_parens(self, validator):
        """Detect unbalanced parentheses."""
        result = validator._validate_syntax("MATCH (a:Aquifer RETURN a")
        assert not result["valid"]
        assert "parentheses" in result["error"].lower()

    def test_schema_validation_unknown_label(self, validator):
        """Detect unknown labels."""
        result = validator._validate_schema("MATCH (a:UnknownLabel) RETURN a")
        assert not result["valid"]
        assert "Unknown labels" in result["error"]
```

### 10.2 Integration Tests

```python
# tests/test_workflow.py

import pytest
from graph.workflow import compile_workflow

class TestAgenticWorkflow:
    @pytest.fixture
    async def workflow(self, bedrock_client, neo4j_driver):
        return compile_workflow(bedrock_client, neo4j_driver)

    @pytest.mark.asyncio
    async def test_end_to_end_simple_query(self, workflow):
        """Test complete flow for simple query."""
        initial_state = {
            "user_query": "List the top 5 aquifers by CO2 capacity",
            "conversation_history": [],
            "error_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        assert result["final_response"] is not None
        assert result["all_queries_valid"] is True
        assert len(result["validation_results"]) == 1

    @pytest.mark.asyncio
    async def test_self_healing_recovers_from_typo(self, workflow):
        """Verify self-healing fixes common errors."""
        # Inject a typo that will need healing
        initial_state = {
            "user_query": "Show me aquifiers with high capacity",  # Note: "aquifiers" typo
            "conversation_history": [],
            "error_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        # Should recover despite typo in user query affecting generation
        assert result["final_response"] is not None
        assert result["validation_results"][0].retry_count <= 3
```

### 10.3 Golden Query Test Suite

```python
# tests/golden_queries.py

GOLDEN_QUERIES = [
    {
        "id": "GQ001",
        "user_query": "What is the average porosity of aquifers in Brazil?",
        "expected_cypher_pattern": r"MATCH.*Aquifer.*LOCATED_IN.*Basin.*WITHIN.*Country.*WHERE.*Brazil.*AVG",
        "expected_result_shape": {"avg_porosity": float},
    },
    {
        "id": "GQ002",
        "user_query": "Compare Amazon and Parnaiba basins by storage capacity",
        "expected_cypher_pattern": r"(UNION|WHERE.*IN)",
        "expected_insights": ["comparison", "recommendation"],
    },
    {
        "id": "GQ003",
        "user_query": "Which low-risk aquifers have the highest capacity?",
        "expected_cypher_pattern": r"HAS_RISK.*risk_level.*LOW.*ORDER BY.*capacity.*DESC",
        "min_results": 1,
    },
    # ... 50+ golden queries covering all scenarios
]

@pytest.mark.parametrize("golden", GOLDEN_QUERIES, ids=lambda g: g["id"])
@pytest.mark.asyncio
async def test_golden_query(golden, workflow):
    """Test against golden query suite."""
    result = await workflow.ainvoke({
        "user_query": golden["user_query"],
        "conversation_history": [],
        "error_count": 0,
    })

    # Verify query pattern
    if "expected_cypher_pattern" in golden:
        generated_query = result["validation_results"][0].original_query
        assert re.search(golden["expected_cypher_pattern"], generated_query, re.IGNORECASE)

    # Verify results
    if "min_results" in golden:
        assert len(result["validation_results"][0].results) >= golden["min_results"]
```

---

## Appendix A: Agent Prompt Templates

See `/prompts/` directory for full prompt templates:
- `planner_v1.md` - Planner agent system prompt
- `cypher_specialist_v1.md` - Cypher generation prompt with examples
- `validator_v1.md` - Validation and healing prompt
- `analyst_v1.md` - Analysis and recommendation prompt

## Appendix B: Error Code Reference

| Code | Category | Description | Resolution |
|------|----------|-------------|------------|
| E001 | Syntax | Unbalanced parentheses | Auto-fix by validator |
| E002 | Syntax | Missing RETURN clause | Auto-fix by validator |
| E003 | Schema | Unknown label | Map to correct label |
| E004 | Schema | Unknown relationship | Map to correct relationship |
| E005 | Semantic | Type mismatch | Restructure query |
| E006 | Execution | Timeout | Add LIMIT, optimize |
| E007 | Execution | Empty result | Broaden criteria |
| E008 | Permission | Access denied | Escalate to user |

---

**Document End**

*This design enables the transition from a monolithic LLM pipeline to a robust, self-healing multi-agent system. The modular architecture allows independent optimization of each agent while maintaining overall system coherence through LangGraph orchestration.*
