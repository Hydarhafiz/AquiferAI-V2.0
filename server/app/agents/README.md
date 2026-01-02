# AquiferAI V2.0 Agent Implementations

This directory contains the four core agents of the AquiferAI multi-agent system, implemented as LangGraph nodes.

## Architecture Overview

```
User Query → Planner → Cypher Specialist → Validator → Analyst → Response
             ↓          ↓                    ↓          ↓
             Plan       Queries              Results    Insights
```

## Agents

### 1. Planner Agent ([planner.py](planner.py))
**Purpose**: Query decomposition and complexity classification

**Input**:
- `user_query`: Natural language question
- `session_id`: Optional conversation context

**Output**:
- `QueryPlan`: Complexity classification + sub-tasks

**Key Features**:
- 90+ line system prompt with full Neo4j schema
- 3-tier complexity: SIMPLE / COMPOUND / ANALYTICAL
- Example-based classification
- Fallback plan on LLM errors
- Temperature: 0.1 (deterministic)

**Example**:
```python
Query: "Recommend best aquifer for 500 Mt CO2 with low risk"
→ Complexity: ANALYTICAL
→ Sub-tasks:
  1. Find aquifers with capacity >= 500 Mt
  2. Filter for low seismic risk
  3. Rank by technical suitability
```

---

### 2. Cypher Specialist Agent ([cypher_specialist.py](cypher_specialist.py))
**Purpose**: Neo4j Cypher query generation

**Input**:
- `query_plan`: Plan from Planner agent

**Output**:
- `List[CypherQuery]`: One query per sub-task

**Key Features**:
- 150+ line system prompt with query patterns
- Pattern library for common operations
- Parameterized queries for safety
- Auto-LIMIT for unbounded queries
- Temperature: 0.1 (precise)

**Example**:
```cypher
Sub-task: "Find aquifers with capacity >= 500 Mt"
→ Generated:
MATCH (a:Aquifer)-[:HAS_RISK]->(r:RiskAssessment)
WHERE a.co2_storage_capacity_mt >= 500
OPTIONAL MATCH (a)-[:LOCATED_IN]->(b:Basin)
RETURN a, b, r
ORDER BY a.co2_storage_capacity_mt DESC
LIMIT 20
```

---

### 3. Validator Agent ([validator.py](validator.py))
**Purpose**: Query validation and self-healing

**Input**:
- `generated_queries`: List of Cypher queries

**Output**:
- `List[ValidationResult]`: Execution results + metadata

**Key Features**:
- Static syntax validation (parentheses, brackets, clauses)
- Neo4j execution via `app.core.neo4j.execute_cypher_query()`
- Self-healing loop (max 3 retries)
- LLM-based query fixing with temperature 0.0
- Execution timing in milliseconds
- Detailed error messages and healing explanations

**Example**:
```python
Original: "MATCH (a:Aquifier) RETURN a"  # Typo
→ Static validation fails: "Unknown label"
→ LLM healing: "MATCH (a:Aquifer) RETURN a"  # Fixed
→ Execute healed query
→ Status: HEALED, retry_count: 1
```

**Functions**:
- `validate_syntax(query)`: Static checks
- `heal_query(query, error, llm)`: LLM-based fix
- `validate_and_execute(query, llm, state)`: Main loop

---

### 4. Analyst Agent ([analyst.py](analyst.py))
**Purpose**: Result synthesis and prescriptive recommendations

**Input**:
- `validation_results`: Query execution results
- `user_query`: Original question for context

**Output**:
- `AnalysisReport`: Insights, recommendations, follow-ups

**Key Features**:
- 100+ line domain knowledge system prompt
- Technical parameter interpretation:
  - Porosity: >0.20 excellent, 0.15-0.20 good
  - Permeability: >200 md excellent, 100-200 md good
  - Depth: 800-2000m ideal for supercritical CO2
- Suitability scoring heuristics
- Prescriptive (not just descriptive) recommendations
- Follow-up question generation
- Visualization hints for frontend
- Temperature: 0.3 (creative insights)

**Example**:
```python
Results: 3 aquifers with capacity >500 Mt, low risk
→ Analysis:
  Summary: "Amazon-347 is the top candidate with 892 Mt capacity..."
  Insights:
    - "Amazon-347 can store emissions for 178+ years"
    - "All candidates meet safety requirements"
  Recommendations:
    - "Prioritize Amazon-347 for feasibility study" (HIGH)
    - "Evaluate Permian-521 as backup" (MEDIUM)
  Follow-ups:
    - "What are the permeability values?"
    - "Are there existing wells nearby?"
```

---

## Testing

Run the comprehensive test suite:

```bash
cd server
python tests/unit/test_agents.py
```

**Prerequisites**:
- Ollama service running: `ollama serve`
- Models pulled: Run `tests/setup_ollama.sh`
- Neo4j running (optional for full validation tests)

**Test Coverage**:
1. Simple query planning
2. Analytical query planning
3. Cypher generation
4. Valid query validation
5. Self-healing with broken query
6. Analyst report generation
7. End-to-end workflow (all 4 agents)

---

## Integration with Workflow

Agents are imported in [app/graph/workflow.py](../graph/workflow.py):

```python
from app.agents.planner import plan_node
from app.agents.cypher_specialist import generate_cypher_node
from app.agents.validator import validate_node
from app.agents.analyst import analyze_node

workflow = StateGraph(AgentState)
workflow.add_node("plan", plan_node)
workflow.add_node("generate_cypher", generate_cypher_node)
workflow.add_node("validate", validate_node)
workflow.add_node("analyze", analyze_node)
# ... edges and compilation
```

---

## LLM Models Used

**Development (Ollama)**:
- Planner: `llama3.2:3b` (fast, 2GB)
- Cypher Specialist: `qwen2.5-coder:7b` (code-optimized, 4.7GB)
- Validator: `llama3.2:3b` (fast, 2GB)
- Analyst: `llama3:8b` (good reasoning, 4.7GB)

**Production (AWS Bedrock - Phase 4)**:
- Planner: `claude-3-5-haiku-20241022-v1:0`
- Cypher Specialist: `claude-3-5-sonnet-20241022-v2:0`
- Validator: `claude-3-5-haiku-20241022-v1:0`
- Analyst: `claude-3-5-sonnet-20241022-v2:0`

Provider switching via environment variable:
```bash
export LLM_PROVIDER=ollama    # Local development
export LLM_PROVIDER=bedrock   # Production (Phase 4)
```

---

## Expert Mode

When `expert_mode=True` in the state:
- Execution trace is captured for each agent
- Detailed timing and retry information
- Query healing explanations
- Full execution path visibility

Used by the frontend Expert Mode feature (Phase 2).

---

## Error Handling

All agents implement graceful degradation:
- **Planner**: Falls back to SIMPLE plan with single subtask
- **Cypher Specialist**: Falls back to basic `MATCH (a:Aquifer) RETURN a LIMIT 10`
- **Validator**: Reports validation errors with suggestions
- **Analyst**: Falls back to basic summary when LLM fails

Error count is tracked in `state["error_count"]` for monitoring.

---

## Next Steps

- **Task 1.4**: Set up Neo4j seeding and Docker Compose
- **Task 1.5**: Wire agents to FastAPI endpoints
- **Phase 2**: Build frontend Expert Mode UI
- **Phase 4**: Deploy to AWS with Bedrock models

---

**Implemented**: January 3, 2026
**Version**: Task 1.3 Complete
**Total Code**: ~1,420 lines across 4 agents + test suite
