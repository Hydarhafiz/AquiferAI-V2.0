# AquiferAI V2.0 Implementation Roadmap

## Zero-Budget Development with "Golden Hour" Deployment Strategy

**Document Version:** 1.0
**Last Updated:** January 2026
**Budget:** $0 Development | <$10 Deployment

---

## Executive Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION TIMELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PHASE 1              PHASE 2              PHASE 3           PHASE 4       │
│   ────────             ────────             ────────           ────────      │
│   Brain Refactor       Expert Interface     Cloud Prep         Golden Hour  │
│   (Local)              (Local)              (Local)            (AWS)        │
│                                                                              │
│   ┌─────────┐          ┌─────────┐          ┌─────────┐       ┌─────────┐   │
│   │LangGraph│          │  React  │          │Terraform│       │ 2-Hour  │   │
│   │ Agents  │    →     │   UI    │    →     │ Docker  │   →   │  Demo   │   │
│   │ Ollama  │          │ Monaco  │          │ Seeding │       │ Metrics │   │
│   └─────────┘          └─────────┘          └─────────┘       └─────────┘   │
│                                                                              │
│   Cost: $0             Cost: $0             Cost: $0          Cost: ~$5-8   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Development Environment Setup

### Prerequisites (All Free)

```bash
# Required software
- Docker Desktop (Free for personal use)
- Node.js 18+ (Free)
- Python 3.11+ (Free)
- Git (Free)
- VS Code (Free)

# Ollama models to pull
ollama pull qwen2.5-coder:7b    # Cypher generation (~4.7GB)
ollama pull llama3:8b           # Analysis (~4.7GB)
ollama pull llama3.2:3b         # Fast planning (~2GB) - NEW for agents
```

### Project Structure

```
aquifer-ai-v2/
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph agents
│   │   │   ├── __init__.py
│   │   │   ├── planner.py
│   │   │   ├── cypher_specialist.py
│   │   │   ├── validator.py
│   │   │   └── analyst.py
│   │   ├── core/
│   │   │   ├── config.py        # Environment-based config
│   │   │   └── llm_provider.py  # Strategy Pattern implementation
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   └── workflow.py      # LangGraph workflow
│   │   ├── services/
│   │   │   ├── neo4j_service.py
│   │   │   └── cache_service.py
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── expert-mode/     # New Expert Mode components
│   │   │   └── visualizations/
│   │   └── ...
│   ├── Dockerfile
│   └── package.json
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── seed-data/
│       └── seed_neo4j.py
├── scripts/
│   ├── golden-hour-deploy.sh
│   ├── golden-hour-teardown.sh
│   └── capture-metrics.sh
└── .env.example
```

---

# Phase 1: The Brain Refactor (Local)

## Objective
Implement LangGraph multi-agent system with Ollama, designed for seamless Bedrock switching.

## Duration Estimate
5-7 working sessions

---

## Task 1.1: LLM Provider Strategy Pattern

### Description
Create an abstraction layer that allows switching between Ollama (dev) and Bedrock (prod) via environment variable.

### Implementation

```python
# backend/app/core/llm_provider.py

from abc import ABC, abstractmethod
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel
import os
import httpx
from enum import Enum

class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    BEDROCK = "bedrock"

class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """Generate structured output using a Pydantic model."""
        pass


class OllamaClient(BaseLLMClient):
    """Ollama client for local development."""

    # Model mapping: logical name -> Ollama model
    MODEL_MAP = {
        "planner": "llama3.2:3b",           # Fast, for planning
        "cypher-specialist": "qwen2.5-coder:7b",  # Best for code
        "validator": "llama3.2:3b",          # Fast, for validation
        "analyst": "llama3:8b",              # Good reasoning
    }

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        ollama_model = self.MODEL_MAP.get(model, model)

        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    async def generate_structured(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """
        For Ollama, we use JSON mode + manual parsing.
        """
        # Add JSON schema instruction to system message
        schema = response_model.model_json_schema()
        json_instruction = f"""
You must respond with valid JSON matching this schema:
{schema}

Respond ONLY with the JSON object, no other text.
"""

        enhanced_messages = messages.copy()
        if enhanced_messages[0]["role"] == "system":
            enhanced_messages[0]["content"] += f"\n\n{json_instruction}"
        else:
            enhanced_messages.insert(0, {"role": "system", "content": json_instruction})

        ollama_model = self.MODEL_MAP.get(model, model)

        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": ollama_model,
                "messages": enhanced_messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": temperature}
            }
        )
        response.raise_for_status()

        content = response.json()["message"]["content"]
        return response_model.model_validate_json(content)


class BedrockClient(BaseLLMClient):
    """AWS Bedrock client for production."""

    MODEL_MAP = {
        "planner": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "cypher-specialist": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "validator": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "analyst": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    }

    def __init__(self, region: str = "us-east-1"):
        # Only import boto3 when needed (not installed in dev)
        import boto3
        from anthropic import AnthropicBedrock

        self.client = AnthropicBedrock(aws_region=region)
        self.region = region

    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        bedrock_model = self.MODEL_MAP.get(model, model)

        # Convert to Anthropic format
        system_msg = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        response = self.client.messages.create(
            model=bedrock_model,
            max_tokens=max_tokens,
            system=system_msg,
            messages=anthropic_messages,
            temperature=temperature,
        )

        return response.content[0].text

    async def generate_structured(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """Use instructor for structured outputs with Bedrock."""
        import instructor

        bedrock_model = self.MODEL_MAP.get(model, model)

        # Wrap with instructor
        client = instructor.from_anthropic(self.client)

        # Extract system message
        system_msg = None
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        return client.messages.create(
            model=bedrock_model,
            max_tokens=4096,
            system=system_msg,
            messages=anthropic_messages,
            response_model=response_model,
            temperature=temperature,
        )


def get_llm_client() -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on environment.

    Usage:
        LLM_PROVIDER=ollama  -> OllamaClient (local dev)
        LLM_PROVIDER=bedrock -> BedrockClient (production)
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == LLMProvider.BEDROCK:
        return BedrockClient(region=os.getenv("AWS_REGION", "us-east-1"))
    else:
        return OllamaClient(base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))


# Dependency injection for FastAPI
from functools import lru_cache

@lru_cache()
def get_cached_llm_client() -> BaseLLMClient:
    """Cached LLM client for dependency injection."""
    return get_llm_client()
```

### Definition of Done
- [ ] `OllamaClient` successfully generates text with `llama3.2:3b`
- [ ] `OllamaClient` generates structured JSON with Pydantic models
- [ ] `BedrockClient` compiles without errors (tested in Phase 4)
- [ ] `LLM_PROVIDER` env var switches between clients
- [ ] Unit tests pass for both clients (mock Bedrock)

### Zero-Cost Workarounds
| Challenge | Workaround |
|-----------|------------|
| Bedrock API testing | Use mocks; real test in Golden Hour |
| Instructor library | Use JSON mode + manual parsing for Ollama |
| Slow Ollama responses | Use smaller `llama3.2:3b` for Planner/Validator |

---

## Task 1.2: LangGraph State & Workflow

### Description
Implement the core LangGraph workflow with state management.

### Implementation

```python
# backend/app/graph/state.py

from typing import TypedDict, List, Optional, Annotated, Any
from langgraph.graph import add_messages
from pydantic import BaseModel

class SubTask(BaseModel):
    task_id: str
    description: str
    query_type: str
    required_entities: List[str]

class QueryPlan(BaseModel):
    original_query: str
    complexity: str
    sub_tasks: List[SubTask]
    reasoning: str

class CypherQuery(BaseModel):
    query: str
    explanation: str
    expected_columns: List[str]

class ValidationResult(BaseModel):
    status: str  # valid, syntax_error, schema_error, execution_error
    original_query: str
    corrected_query: Optional[str] = None
    error_message: Optional[str] = None
    results: Optional[List[dict]] = None
    execution_time_ms: Optional[float] = None
    retry_count: int = 0

class AnalysisReport(BaseModel):
    summary: str
    insights: List[dict]
    recommendations: List[dict]
    follow_up_questions: List[str]
    visualization_hints: List[str]

class AgentState(TypedDict):
    """Shared state across all agents in the graph."""

    # Input
    user_query: str
    session_id: str
    expert_mode: bool

    # Conversation
    messages: Annotated[List[dict], add_messages]

    # Planner output
    query_plan: Optional[QueryPlan]

    # Cypher Specialist output
    generated_queries: List[CypherQuery]

    # Validator output
    validation_results: List[ValidationResult]
    all_queries_valid: bool
    total_retries: int

    # Analyst output
    analysis_report: Optional[AnalysisReport]

    # Control flow
    error_count: int
    should_escalate: bool

    # Final output
    final_response: str
    execution_trace: Optional[dict]  # For expert mode
```

```python
# backend/app/graph/workflow.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import AgentState
from app.agents.planner import plan_node
from app.agents.cypher_specialist import generate_cypher_node
from app.agents.validator import validate_node
from app.agents.analyst import analyze_node
from app.core.llm_provider import get_llm_client
import time

def create_workflow():
    """Create the LangGraph workflow."""

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("generate_cypher", generate_cypher_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("format_response", format_response_node)
    workflow.add_node("handle_error", handle_error_node)

    # Define edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "generate_cypher")
    workflow.add_edge("generate_cypher", "validate")

    # Conditional routing after validation
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "analyze": "analyze",
            "handle_error": "handle_error"
        }
    )

    workflow.add_edge("analyze", "format_response")
    workflow.add_edge("format_response", END)
    workflow.add_edge("handle_error", END)

    return workflow


def route_after_validation(state: AgentState) -> str:
    """Determine next step based on validation results."""
    if state.get("all_queries_valid", False):
        return "analyze"
    elif state.get("error_count", 0) > 2:
        return "handle_error"
    else:
        # Proceed with partial results
        return "analyze"


async def format_response_node(state: AgentState) -> dict:
    """Format the final response for the user."""
    report = state.get("analysis_report")

    if not report:
        return {"final_response": "I couldn't generate an analysis. Please try rephrasing your question."}

    # Build markdown response
    response_parts = [
        f"## Summary\n{report.summary}",
        "\n## Key Insights",
        *[f"- **{i.get('title', 'Insight')}**: {i.get('description', '')}" for i in report.insights],
        "\n## Recommendations",
        *[f"{idx+1}. **{r.get('action', '')}** - {r.get('rationale', '')}" for idx, r in enumerate(report.recommendations)],
        "\n## Suggested Follow-up Questions",
        *[f"- {q}" for q in report.follow_up_questions],
    ]

    response = "\n".join(response_parts)

    # Build execution trace for expert mode
    execution_trace = None
    if state.get("expert_mode"):
        execution_trace = {
            "plan": state.get("query_plan").model_dump() if state.get("query_plan") else None,
            "queries": [
                {
                    "query": vr.original_query,
                    "corrected": vr.corrected_query,
                    "status": vr.status,
                    "execution_time_ms": vr.execution_time_ms,
                    "retry_count": vr.retry_count,
                }
                for vr in state.get("validation_results", [])
            ],
            "total_retries": state.get("total_retries", 0),
        }

    return {
        "final_response": response,
        "execution_trace": execution_trace,
    }


async def handle_error_node(state: AgentState) -> dict:
    """Handle cases where queries failed."""
    failed = [r for r in state.get("validation_results", []) if r.status != "valid"]

    response = f"""
## Unable to Complete Analysis

I encountered some issues processing your query:

{chr(10).join(f"- {r.error_message}" for r in failed[:3])}

**Suggestions:**
- Try simplifying your question
- Be more specific about which aquifers or basins you're interested in
- Check if the entity names are spelled correctly

Would you like me to try a different approach?
"""

    return {
        "final_response": response,
        "should_escalate": True,
    }


def compile_workflow():
    """Compile workflow with memory for conversation persistence."""
    workflow = create_workflow()
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Singleton compiled workflow
_compiled_workflow = None

def get_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow()
    return _compiled_workflow
```

### Definition of Done
- [ ] State dataclass properly typed with all fields
- [ ] Workflow compiles without errors
- [ ] Can trace execution path through all nodes
- [ ] Memory checkpointer persists conversation state
- [ ] Conditional routing works correctly

---

## Task 1.3: Agent Implementations

### Description
Implement each agent as a node function.

### Planner Agent

```python
# backend/app/agents/planner.py

from app.graph.state import AgentState, QueryPlan, SubTask
from app.core.llm_provider import get_llm_client
import json

PLANNER_SYSTEM_PROMPT = """
You are the Planner Agent for a saline aquifer analytics system.

Your job is to analyze user questions and create an execution plan.

## Neo4j Schema
- (:Aquifer) - Properties: name, depth_m, porosity, permeability_md, temperature_c,
  pressure_mpa, salinity_ppm, co2_storage_capacity_mt, latitude, longitude, cluster_id
- (:Basin) - Properties: name, area_km2
- (:Country) - Properties: name, region
- (:RiskAssessment) - Properties: risk_level (LOW/MEDIUM/HIGH), seismic_risk, regulatory_score
- Relationships: (Aquifer)-[:LOCATED_IN]->(Basin)-[:WITHIN]->(Country)
                 (Aquifer)-[:HAS_RISK]->(RiskAssessment)

## Classification Rules
- SIMPLE: Single entity lookup (1 sub-task)
- COMPOUND: Multiple entities or comparisons (2-3 sub-tasks)
- ANALYTICAL: Aggregations, rankings, risk analysis (2-4 sub-tasks)

Respond with a JSON object containing:
- original_query: the user's question
- complexity: "simple", "compound", or "analytical"
- sub_tasks: array of {task_id, description, query_type, required_entities}
- reasoning: why you chose this decomposition
"""

async def plan_node(state: AgentState) -> dict:
    """Planner agent node - decomposes user query into sub-tasks."""

    llm = get_llm_client()
    user_query = state["user_query"]

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Create an execution plan for: {user_query}"}
    ]

    try:
        plan = await llm.generate_structured(
            model="planner",
            messages=messages,
            response_model=QueryPlan,
            temperature=0.1
        )
    except Exception as e:
        # Fallback to simple plan
        plan = QueryPlan(
            original_query=user_query,
            complexity="simple",
            sub_tasks=[
                SubTask(
                    task_id="task_1",
                    description=user_query,
                    query_type="lookup",
                    required_entities=["Aquifer"]
                )
            ],
            reasoning=f"Fallback due to error: {str(e)}"
        )

    return {
        "query_plan": plan,
        "generated_queries": [],
        "validation_results": [],
    }
```

### Cypher Specialist Agent

```python
# backend/app/agents/cypher_specialist.py

from app.graph.state import AgentState, CypherQuery
from app.core.llm_provider import get_llm_client

CYPHER_SPECIALIST_PROMPT = """
You are the Cypher Specialist Agent for a Neo4j-based saline aquifer database.

## Schema Reference
```
(:Aquifer {
    name: STRING, depth_m: FLOAT, porosity: FLOAT, permeability_md: FLOAT,
    temperature_c: FLOAT, pressure_mpa: FLOAT, salinity_ppm: INTEGER,
    co2_storage_capacity_mt: FLOAT, latitude: FLOAT, longitude: FLOAT, cluster_id: INTEGER
})
(:Basin {name: STRING, area_km2: FLOAT})
(:Country {name: STRING, region: STRING})
(:RiskAssessment {risk_level: STRING, seismic_risk: STRING, regulatory_score: FLOAT})

Relationships:
(Aquifer)-[:LOCATED_IN]->(Basin)
(Basin)-[:WITHIN]->(Country)
(Aquifer)-[:HAS_RISK]->(RiskAssessment)
```

## Rules
1. Use MATCH for reading data
2. Always include RETURN clause
3. Use LIMIT for unbounded queries (default: 20)
4. Use OPTIONAL MATCH for potentially missing relationships
5. Property names are case-sensitive

## Query Patterns
- Single aquifer: MATCH (a:Aquifer {name: $name}) RETURN a
- Basin aquifers: MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin {name: $basin}) RETURN a
- With risk: MATCH (a:Aquifer)-[:HAS_RISK]->(r:RiskAssessment) WHERE r.risk_level = $level RETURN a, r
- Top capacity: MATCH (a:Aquifer) RETURN a ORDER BY a.co2_storage_capacity_mt DESC LIMIT 10

Respond with JSON: {query, explanation, expected_columns}
"""

async def generate_cypher_node(state: AgentState) -> dict:
    """Cypher Specialist agent - generates Cypher queries for each sub-task."""

    llm = get_llm_client()
    plan = state["query_plan"]
    queries = []

    for subtask in plan.sub_tasks:
        messages = [
            {"role": "system", "content": CYPHER_SPECIALIST_PROMPT},
            {"role": "user", "content": f"""
Generate a Cypher query for this task:

Task: {subtask.description}
Query Type: {subtask.query_type}
Required Entities: {subtask.required_entities}

Original user question: {plan.original_query}
"""}
        ]

        try:
            query = await llm.generate_structured(
                model="cypher-specialist",
                messages=messages,
                response_model=CypherQuery,
                temperature=0.1
            )
            queries.append(query)
        except Exception as e:
            # Fallback query
            queries.append(CypherQuery(
                query="MATCH (a:Aquifer) RETURN a.name, a.co2_storage_capacity_mt LIMIT 10",
                explanation=f"Fallback query due to error: {str(e)}",
                expected_columns=["a.name", "a.co2_storage_capacity_mt"]
            ))

    return {"generated_queries": queries}
```

### Validator Agent

```python
# backend/app/agents/validator.py

from app.graph.state import AgentState, ValidationResult, CypherQuery
from app.core.llm_provider import get_llm_client
from app.services.neo4j_service import get_neo4j_service
import re
import time

VALIDATOR_HEALING_PROMPT = """
You are the Validator Agent. Fix this broken Cypher query.

## Common Fixes
- Unknown label → Check spelling (Aquifer not Aquifier)
- Unknown relationship → Use LOCATED_IN, WITHIN, or HAS_RISK
- Unknown property → Check schema for correct property names
- Syntax error → Check parentheses, brackets, clause order

## Schema Reminder
Labels: Aquifer, Basin, Country, RiskAssessment
Relationships: LOCATED_IN, WITHIN, HAS_RISK
Properties: name, depth_m, porosity, permeability_md, co2_storage_capacity_mt, risk_level

Return ONLY the corrected Cypher query, nothing else.
"""

MAX_RETRIES = 3

async def validate_node(state: AgentState) -> dict:
    """Validator agent - validates and executes Cypher queries with self-healing."""

    llm = get_llm_client()
    neo4j = get_neo4j_service()

    results = []
    total_retries = 0
    all_valid = True

    for cypher_query in state["generated_queries"]:
        result = await validate_and_execute(cypher_query, llm, neo4j)
        results.append(result)
        total_retries += result.retry_count

        if result.status != "valid":
            all_valid = False

    return {
        "validation_results": results,
        "all_queries_valid": all_valid,
        "total_retries": total_retries,
        "error_count": sum(1 for r in results if r.status != "valid"),
    }


async def validate_and_execute(
    cypher_query: CypherQuery,
    llm,
    neo4j
) -> ValidationResult:
    """Validate, execute, and potentially heal a single query."""

    current_query = cypher_query.query
    retry_count = 0

    while retry_count <= MAX_RETRIES:
        # Step 1: Static validation
        syntax_errors = validate_syntax(current_query)
        if syntax_errors:
            if retry_count >= MAX_RETRIES:
                return ValidationResult(
                    status="syntax_error",
                    original_query=cypher_query.query,
                    error_message="; ".join(syntax_errors),
                    retry_count=retry_count
                )
            current_query = await heal_query(current_query, syntax_errors[0], llm)
            retry_count += 1
            continue

        # Step 2: Execute query
        try:
            start_time = time.perf_counter()
            results = await neo4j.execute_query(current_query)
            execution_time = (time.perf_counter() - start_time) * 1000

            return ValidationResult(
                status="valid",
                original_query=cypher_query.query,
                corrected_query=current_query if current_query != cypher_query.query else None,
                results=results,
                execution_time_ms=execution_time,
                retry_count=retry_count
            )

        except Exception as e:
            error_msg = str(e)

            if retry_count >= MAX_RETRIES:
                return ValidationResult(
                    status="execution_error",
                    original_query=cypher_query.query,
                    error_message=error_msg,
                    retry_count=retry_count
                )

            current_query = await heal_query(current_query, error_msg, llm)
            retry_count += 1

    return ValidationResult(
        status="execution_error",
        original_query=cypher_query.query,
        error_message="Max retries exceeded",
        retry_count=retry_count
    )


def validate_syntax(query: str) -> list:
    """Static syntax validation."""
    errors = []

    # Check balanced parentheses
    if query.count('(') != query.count(')'):
        errors.append("Unbalanced parentheses")

    # Check balanced brackets
    if query.count('[') != query.count(']'):
        errors.append("Unbalanced brackets")

    # Check required clauses
    query_upper = query.upper()
    if 'MATCH' not in query_upper and 'CREATE' not in query_upper:
        errors.append("Missing MATCH or CREATE clause")

    if 'RETURN' not in query_upper:
        errors.append("Missing RETURN clause")

    return errors


async def heal_query(query: str, error: str, llm) -> str:
    """Use LLM to heal a broken query."""

    messages = [
        {"role": "system", "content": VALIDATOR_HEALING_PROMPT},
        {"role": "user", "content": f"Fix this query:\n\n{query}\n\nError: {error}"}
    ]

    corrected = await llm.generate(
        model="validator",
        messages=messages,
        temperature=0.0,
        max_tokens=500
    )

    # Clean up response
    corrected = corrected.strip()
    if corrected.startswith("```"):
        corrected = corrected.split("```")[1]
        if corrected.startswith("cypher"):
            corrected = corrected[6:]

    return corrected.strip()
```

### Analyst Agent

```python
# backend/app/agents/analyst.py

from app.graph.state import AgentState, AnalysisReport
from app.core.llm_provider import get_llm_client

ANALYST_PROMPT = """
You are the Analyst Agent for a CO2 storage site advisory system.

## Your Mission
Transform query results into PRESCRIPTIVE analytics - tell users what to DO.

## Domain Context
- Saline aquifers store CO2 underground permanently
- Key factors: porosity (>15% good), permeability (>100 md good), depth (>800m keeps CO2 supercritical)
- Risk levels: LOW (safe), MEDIUM (needs monitoring), HIGH (avoid)
- Capacity measured in megatonnes (Mt) - power plants emit ~3-5 Mt/year

## Output Format
Provide:
1. summary: 2-3 sentence executive summary
2. insights: Array of {type, title, description, confidence}
3. recommendations: Array of {priority (1-5), action, rationale, expected_outcome}
4. follow_up_questions: 2-3 suggested next questions
5. visualization_hints: Charts/maps to display ["bar_chart", "map", "table"]

Be specific and actionable. Don't just describe - RECOMMEND.
"""

async def analyze_node(state: AgentState) -> dict:
    """Analyst agent - synthesizes results into prescriptive recommendations."""

    llm = get_llm_client()

    # Collect all successful results
    all_results = []
    for vr in state.get("validation_results", []):
        if vr.results:
            all_results.extend(vr.results)

    if not all_results:
        return {
            "analysis_report": AnalysisReport(
                summary="No data was retrieved to analyze.",
                insights=[],
                recommendations=[],
                follow_up_questions=["Could you rephrase your question?"],
                visualization_hints=[]
            )
        }

    # Format results for LLM
    results_text = format_results(all_results)

    messages = [
        {"role": "system", "content": ANALYST_PROMPT},
        {"role": "user", "content": f"""
Analyze these results and provide prescriptive recommendations.

## User's Question
{state["query_plan"].original_query}

## Query Results
{results_text}

Provide actionable analysis with specific recommendations.
"""}
    ]

    try:
        report = await llm.generate_structured(
            model="analyst",
            messages=messages,
            response_model=AnalysisReport,
            temperature=0.3
        )
    except Exception as e:
        report = AnalysisReport(
            summary=f"Analysis completed. Found {len(all_results)} records.",
            insights=[{"type": "data", "title": "Data Retrieved", "description": f"{len(all_results)} aquifer records found", "confidence": 1.0}],
            recommendations=[],
            follow_up_questions=["What specific aspect would you like me to analyze?"],
            visualization_hints=["table"]
        )

    return {"analysis_report": report}


def format_results(results: list, max_rows: int = 20) -> str:
    """Format query results for LLM consumption."""
    if not results:
        return "No results"

    if len(results) > max_rows:
        return f"Total: {len(results)} records\nSample (first {max_rows}):\n{results[:max_rows]}"

    return str(results)
```

### Definition of Done
- [ ] All 4 agents generate valid outputs
- [ ] Planner correctly classifies simple/compound/analytical queries
- [ ] Cypher Specialist generates valid Cypher 80%+ of the time
- [ ] Validator successfully heals broken queries
- [ ] Analyst produces actionable recommendations
- [ ] End-to-end pipeline works with sample queries

---

## Task 1.4: Neo4j Service & Local Testing

### Implementation

```python
# backend/app/services/neo4j_service.py

from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any
import os

class Neo4jService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    async def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def execute_query(self, query: str, params: dict = None) -> List[Dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    async def get_schema(self) -> dict:
        """Get database schema for autocomplete."""
        labels_query = "CALL db.labels()"
        rels_query = "CALL db.relationshipTypes()"
        props_query = "CALL db.propertyKeys()"

        async with self.driver.session() as session:
            labels = [r["label"] async for r in await session.run(labels_query)]
            rels = [r["relationshipType"] async for r in await session.run(rels_query)]
            props = [r["propertyKey"] async for r in await session.run(props_query)]

        return {"labels": labels, "relationships": rels, "properties": props}


# Singleton
_neo4j_service = None

def get_neo4j_service() -> Neo4jService:
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
```

### Docker Compose for Local Development

```yaml
# docker-compose.yml

version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: aquifer-neo4j
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/aquifer_password_123
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:15-alpine
    container_name: aquifer-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=aquifer
      - POSTGRES_PASSWORD=aquifer_password_123
      - POSTGRES_DB=aquifer_chat
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: aquifer-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: aquifer-backend
    ports:
      - "8000:8000"
    environment:
      - LLM_PROVIDER=ollama
      - OLLAMA_URL=http://host.docker.internal:11434
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=aquifer_password_123
      - DATABASE_URL=postgresql://aquifer:aquifer_password_123@postgres:5432/aquifer_chat
      - REDIS_URL=redis://redis:6379
    depends_on:
      neo4j:
        condition: service_healthy
      postgres:
        condition: service_started
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: aquifer-frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host

volumes:
  neo4j_data:
  neo4j_logs:
  postgres_data:
  redis_data:
```

### Definition of Done (Phase 1)
- [ ] Docker Compose starts all services successfully
- [ ] Neo4j accessible at localhost:7474
- [ ] Sample data loaded (50-100 aquifers)
- [ ] End-to-end query: "List top 5 aquifers by capacity" returns results
- [ ] Self-healing demonstrated: intentionally broken query gets fixed
- [ ] Response time <10s for simple queries (Ollama)

### Zero-Cost Workarounds (Phase 1)

| Challenge | Workaround |
|-----------|------------|
| Slow Ollama | Use smaller models (`llama3.2:3b`) for Planner/Validator |
| Limited GPU VRAM | Run one model at a time, unload between calls |
| No Bedrock access | Mock `BedrockClient` in tests |
| Neo4j Enterprise | Use Community edition (sufficient for dev) |

---

# Phase 2: The Expert Interface (Local)

## Objective
Build frontend components for Expert Mode and enhanced visualizations.

## Duration Estimate
4-6 working sessions

---

## Task 2.1: Expert Mode Toggle & State

```typescript
// frontend/src/stores/expertModeStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ExpertModeState {
  enabled: boolean;
  autoExpandQueries: boolean;
  showExecutionTrace: boolean;
  syntaxTheme: 'monokai' | 'github' | 'dracula';

  toggleExpertMode: () => void;
  setAutoExpandQueries: (value: boolean) => void;
  setShowExecutionTrace: (value: boolean) => void;
  setSyntaxTheme: (theme: 'monokai' | 'github' | 'dracula') => void;
}

export const useExpertModeStore = create<ExpertModeState>()(
  persist(
    (set) => ({
      enabled: false,
      autoExpandQueries: true,
      showExecutionTrace: false,
      syntaxTheme: 'monokai',

      toggleExpertMode: () => set((state) => ({ enabled: !state.enabled })),
      setAutoExpandQueries: (value) => set({ autoExpandQueries: value }),
      setShowExecutionTrace: (value) => set({ showExecutionTrace: value }),
      setSyntaxTheme: (theme) => set({ syntaxTheme: theme }),
    }),
    {
      name: 'expert-mode-storage',
    }
  )
);
```

### Definition of Done
- [ ] Toggle persists across page reloads
- [ ] Settings UI in header/sidebar
- [ ] State accessible throughout app

---

## Task 2.2: Cypher Query Panel Component

```typescript
// frontend/src/components/expert-mode/CypherQueryPanel.tsx

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Edit2, Check, Clock, AlertCircle } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useExpertModeStore } from '@/stores/expertModeStore';

interface CypherQueryPanelProps {
  query: string;
  correctedQuery?: string;
  explanation: string;
  executionTimeMs?: number;
  retryCount: number;
  status: 'valid' | 'error';
  onEdit?: (query: string) => void;
}

export const CypherQueryPanel: React.FC<CypherQueryPanelProps> = ({
  query,
  correctedQuery,
  explanation,
  executionTimeMs,
  retryCount,
  status,
  onEdit,
}) => {
  const { enabled, autoExpandQueries } = useExpertModeStore();
  const [isExpanded, setIsExpanded] = useState(autoExpandQueries);
  const [copied, setCopied] = useState(false);

  if (!enabled) return null;

  const displayQuery = correctedQuery || query;
  const wasHealed = correctedQuery && correctedQuery !== query;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(displayQuery);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 border border-gray-700 rounded-lg bg-gray-900">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-300">
            Generated Cypher Query
          </span>
          {wasHealed && (
            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded">
              Self-Healed ({retryCount} retries)
            </span>
          )}
          {status === 'valid' ? (
            <Check className="w-4 h-4 text-green-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400" />
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-700">
          {/* Query Code */}
          <div className="relative">
            <div className="absolute top-2 right-2 flex gap-2">
              <button
                onClick={handleCopy}
                className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white"
                title="Copy query"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
              {onEdit && (
                <button
                  onClick={() => onEdit(displayQuery)}
                  className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white"
                  title="Edit query"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}
            </div>
            <SyntaxHighlighter
              language="cypher"
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                padding: '1rem',
                paddingRight: '4rem',
                background: 'transparent',
                fontSize: '0.875rem',
              }}
              showLineNumbers
            >
              {displayQuery}
            </SyntaxHighlighter>
          </div>

          {/* Explanation */}
          <div className="p-3 border-t border-gray-700 bg-gray-800/50">
            <div className="text-sm text-gray-400">
              <span className="font-medium text-gray-300">What this query does:</span>{' '}
              {explanation}
            </div>
          </div>

          {/* Execution Stats */}
          {executionTimeMs !== undefined && (
            <div className="px-3 py-2 border-t border-gray-700 flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{executionTimeMs.toFixed(1)}ms</span>
              </div>
              {retryCount > 0 && (
                <div>Self-healing attempts: {retryCount}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

### Definition of Done
- [ ] Panel shows/hides based on Expert Mode toggle
- [ ] Syntax highlighting works for Cypher
- [ ] Copy button copies query to clipboard
- [ ] Self-healing indicator shows retry count
- [ ] Execution time displayed

---

## Task 2.3: Query Editor Modal (Monaco)

```typescript
// frontend/src/components/expert-mode/QueryEditorModal.tsx

import React, { useState, useRef } from 'react';
import Editor, { Monaco } from '@monaco-editor/react';
import { X, Play, AlertTriangle, Check } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface QueryEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery: string;
  onQueryExecuted: (results: any) => void;
}

// Cypher language configuration for Monaco
const configureCypherLanguage = (monaco: Monaco) => {
  monaco.languages.register({ id: 'cypher' });

  monaco.languages.setMonarchTokensProvider('cypher', {
    keywords: [
      'MATCH', 'OPTIONAL', 'WHERE', 'RETURN', 'ORDER', 'BY', 'LIMIT', 'SKIP',
      'CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'WITH', 'UNWIND', 'UNION',
      'CALL', 'YIELD', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR',
      'NOT', 'IN', 'STARTS', 'ENDS', 'CONTAINS', 'AS', 'DISTINCT', 'TRUE',
      'FALSE', 'NULL', 'ASC', 'DESC', 'ON', 'INDEX', 'CONSTRAINT'
    ],
    operators: ['=', '<>', '<', '>', '<=', '>=', '+', '-', '*', '/', '%'],
    symbols: /[=><!~?:&|+\-*\/\^%]+/,

    tokenizer: {
      root: [
        [/[a-zA-Z_]\w*/, {
          cases: {
            '@keywords': 'keyword',
            '@default': 'identifier'
          }
        }],
        [/:[A-Z][a-zA-Z0-9]*/, 'type'],  // Labels
        [/\.[a-z][a-zA-Z0-9_]*/, 'variable'],  // Properties
        [/"([^"\\]|\\.)*"/, 'string'],
        [/'([^'\\]|\\.)*'/, 'string'],
        [/\d+/, 'number'],
        [/\/\/.*$/, 'comment'],
      ],
    },
  });

  monaco.languages.setLanguageConfiguration('cypher', {
    brackets: [
      ['(', ')'],
      ['[', ']'],
      ['{', '}'],
    ],
    autoClosingPairs: [
      { open: '(', close: ')' },
      { open: '[', close: ']' },
      { open: '{', close: '}' },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
  });
};

export const QueryEditorModal: React.FC<QueryEditorModalProps> = ({
  isOpen,
  onClose,
  initialQuery,
  onQueryExecuted,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [validationError, setValidationError] = useState<string | null>(null);
  const editorRef = useRef<any>(null);

  const executeMutation = useMutation({
    mutationFn: async (cypher: string) => {
      const response = await api.post('/api/v2/queries/execute', { query: cypher });
      return response.data;
    },
    onSuccess: (data) => {
      onQueryExecuted(data);
      onClose();
    },
    onError: (error: any) => {
      setValidationError(error.response?.data?.detail || 'Query execution failed');
    },
  });

  const validateMutation = useMutation({
    mutationFn: async (cypher: string) => {
      const response = await api.post('/api/v2/queries/validate', { query: cypher });
      return response.data;
    },
    onSuccess: (data) => {
      if (data.valid) {
        setValidationError(null);
      } else {
        setValidationError(data.errors?.join('; ') || 'Invalid query');
      }
    },
  });

  const handleEditorMount = (editor: any, monaco: Monaco) => {
    editorRef.current = editor;
    configureCypherLanguage(monaco);
  };

  const handleValidate = () => {
    validateMutation.mutate(query);
  };

  const handleExecute = () => {
    setValidationError(null);
    executeMutation.mutate(query);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-4xl bg-gray-900 rounded-lg shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Edit Cypher Query</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-700 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Editor */}
        <div className="h-80">
          <Editor
            height="100%"
            defaultLanguage="cypher"
            value={query}
            onChange={(value) => setQuery(value || '')}
            onMount={handleEditorMount}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 2,
            }}
          />
        </div>

        {/* Validation Error */}
        {validationError && (
          <div className="mx-4 mt-2 p-3 bg-red-500/10 border border-red-500/30 rounded flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-red-300">{validationError}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700">
          <button
            onClick={handleValidate}
            disabled={validateMutation.isPending}
            className="px-4 py-2 text-sm rounded bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-50"
          >
            {validateMutation.isPending ? 'Validating...' : 'Validate'}
          </button>
          <button
            onClick={handleExecute}
            disabled={executeMutation.isPending}
            className="px-4 py-2 text-sm rounded bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-2 disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {executeMutation.isPending ? 'Executing...' : 'Run Query'}
          </button>
        </div>
      </div>
    </div>
  );
};
```

### Definition of Done
- [ ] Monaco Editor loads with Cypher syntax highlighting
- [ ] Autocomplete suggests labels, properties (basic)
- [ ] Validate button checks query before execution
- [ ] Execute button runs query and displays results
- [ ] Errors displayed inline

---

## Task 2.4: Execution Trace Timeline

```typescript
// frontend/src/components/expert-mode/ExecutionTrace.tsx

import React from 'react';
import { Brain, Zap, CheckCircle, BarChart3 } from 'lucide-react';

interface AgentTrace {
  name: string;
  durationMs: number;
  status: 'success' | 'error';
  retries?: number;
}

interface ExecutionTraceProps {
  trace: {
    agents: AgentTrace[];
    totalRetries: number;
  };
}

const AGENT_ICONS = {
  planner: Brain,
  'cypher-specialist': Zap,
  validator: CheckCircle,
  analyst: BarChart3,
};

const AGENT_COLORS = {
  planner: 'bg-purple-500',
  'cypher-specialist': 'bg-blue-500',
  validator: 'bg-green-500',
  analyst: 'bg-orange-500',
};

export const ExecutionTrace: React.FC<ExecutionTraceProps> = ({ trace }) => {
  const totalTime = trace.agents.reduce((sum, a) => sum + a.durationMs, 0);

  return (
    <div className="mt-4 p-4 bg-gray-800 rounded-lg">
      <h4 className="text-sm font-medium text-gray-300 mb-3">Execution Trace</h4>

      {/* Timeline */}
      <div className="relative">
        {/* Progress bar */}
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden flex">
          {trace.agents.map((agent, idx) => {
            const width = (agent.durationMs / totalTime) * 100;
            return (
              <div
                key={idx}
                className={`h-full ${AGENT_COLORS[agent.name as keyof typeof AGENT_COLORS] || 'bg-gray-500'}`}
                style={{ width: `${width}%` }}
                title={`${agent.name}: ${agent.durationMs.toFixed(0)}ms`}
              />
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          {trace.agents.map((agent, idx) => {
            const Icon = AGENT_ICONS[agent.name as keyof typeof AGENT_ICONS] || Brain;
            const colorClass = AGENT_COLORS[agent.name as keyof typeof AGENT_COLORS] || 'bg-gray-500';

            return (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <div className={`w-3 h-3 rounded ${colorClass}`} />
                <Icon className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300 capitalize">
                  {agent.name.replace('-', ' ')}
                </span>
                <span className="text-gray-500 ml-auto">
                  {agent.durationMs.toFixed(0)}ms
                </span>
                {agent.retries && agent.retries > 0 && (
                  <span className="text-yellow-500 text-xs">
                    ({agent.retries} retries)
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Total */}
        <div className="mt-3 pt-3 border-t border-gray-700 flex justify-between text-sm">
          <span className="text-gray-400">Total execution time</span>
          <span className="text-white font-medium">{totalTime.toFixed(0)}ms</span>
        </div>
      </div>
    </div>
  );
};
```

### Definition of Done (Phase 2)
- [ ] Expert Mode toggle in header
- [ ] Query panel shows below AI responses
- [ ] Query editor modal with Monaco
- [ ] Execution trace timeline visualization
- [ ] All components responsive on mobile

### Zero-Cost Workarounds (Phase 2)

| Challenge | Workaround |
|-----------|------------|
| Monaco Editor bundle size | Dynamic import with React.lazy() |
| Cypher language support | Custom Monarch tokenizer (minimal) |
| No real-time validation | Validate on button click, not keystroke |

---

# Phase 3: Cloud Prep & Containerization (Local)

## Objective
Prepare infrastructure code and seeding scripts for rapid deployment.

## Duration Estimate
3-4 working sessions

---

## Task 3.1: Production Dockerfiles

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY ./app ./app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile

# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# frontend/nginx.conf

server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Health check endpoint
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # API proxy (for production)
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Task 3.2: Neo4j Seeding Script

```python
# infrastructure/seed-data/seed_neo4j.py

"""
Neo4j Seeding Script for AquiferAI
Populates database with sample aquifer data for demos.

Usage:
    python seed_neo4j.py --uri bolt://localhost:7687 --user neo4j --password xxx
    python seed_neo4j.py --uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password xxx
"""

import argparse
import random
from neo4j import GraphDatabase

# Sample data - 50 aquifers for demo (subset of 100k+ production data)
COUNTRIES = [
    {"name": "Brazil", "region": "South America"},
    {"name": "United States", "region": "North America"},
    {"name": "Australia", "region": "Oceania"},
]

BASINS = [
    {"name": "Amazon Basin", "country": "Brazil", "area_km2": 7050000},
    {"name": "Parnaiba Basin", "country": "Brazil", "area_km2": 660000},
    {"name": "Santos Basin", "country": "Brazil", "area_km2": 350000},
    {"name": "Permian Basin", "country": "United States", "area_km2": 220000},
    {"name": "Gulf Coast Basin", "country": "United States", "area_km2": 500000},
    {"name": "Great Artesian Basin", "country": "Australia", "area_km2": 1700000},
]

AQUIFER_NAMES = [
    "Solimões", "Amazonas-01", "Amazonas-02", "Parnaíba-Central", "Parnaíba-North",
    "Santos-Deep", "Santos-Shallow", "Campos-Offshore", "Permian-West", "Permian-East",
    "Gulf-South", "Gulf-Central", "Artesian-North", "Artesian-South", "Artesian-Central",
]

def generate_aquifer_data(name: str, basin: str) -> dict:
    """Generate realistic aquifer properties."""
    return {
        "name": f"{name}-{random.randint(100, 999)}",
        "depth_m": round(random.uniform(800, 3500), 1),
        "porosity": round(random.uniform(0.08, 0.35), 3),
        "permeability_md": round(random.uniform(10, 500), 1),
        "temperature_c": round(random.uniform(30, 120), 1),
        "pressure_mpa": round(random.uniform(10, 50), 1),
        "salinity_ppm": random.randint(10000, 150000),
        "co2_storage_capacity_mt": round(random.uniform(50, 1000), 1),
        "latitude": round(random.uniform(-30, 40), 4),
        "longitude": round(random.uniform(-80, 150), 4),
        "cluster_id": random.randint(0, 2),
        "basin": basin,
    }

def generate_risk_assessment() -> dict:
    """Generate risk assessment data."""
    risk_level = random.choice(["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH"])
    return {
        "risk_level": risk_level,
        "seismic_risk": random.choice(["LOW", "MEDIUM", "HIGH"]),
        "regulatory_score": round(random.uniform(0.5, 1.0), 2),
    }

def seed_database(uri: str, user: str, password: str, aquifer_count: int = 50):
    """Seed the Neo4j database with sample data."""

    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # Clear existing data
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")

        # Create indexes
        print("Creating indexes...")
        session.run("CREATE INDEX aquifer_name IF NOT EXISTS FOR (a:Aquifer) ON (a.name)")
        session.run("CREATE INDEX aquifer_capacity IF NOT EXISTS FOR (a:Aquifer) ON (a.co2_storage_capacity_mt)")
        session.run("CREATE INDEX basin_name IF NOT EXISTS FOR (b:Basin) ON (b.name)")
        session.run("CREATE INDEX risk_level IF NOT EXISTS FOR (r:RiskAssessment) ON (r.risk_level)")

        # Create countries
        print("Creating countries...")
        for country in COUNTRIES:
            session.run(
                "CREATE (c:Country {name: $name, region: $region})",
                country
            )

        # Create basins with country relationships
        print("Creating basins...")
        for basin in BASINS:
            session.run("""
                MATCH (c:Country {name: $country})
                CREATE (b:Basin {name: $name, area_km2: $area_km2})
                CREATE (b)-[:WITHIN]->(c)
            """, basin)

        # Create aquifers
        print(f"Creating {aquifer_count} aquifers...")
        for i in range(aquifer_count):
            basin = random.choice(BASINS)
            base_name = random.choice(AQUIFER_NAMES)
            aquifer = generate_aquifer_data(base_name, basin["name"])
            risk = generate_risk_assessment()

            session.run("""
                MATCH (b:Basin {name: $basin})
                CREATE (a:Aquifer {
                    name: $name,
                    depth_m: $depth_m,
                    porosity: $porosity,
                    permeability_md: $permeability_md,
                    temperature_c: $temperature_c,
                    pressure_mpa: $pressure_mpa,
                    salinity_ppm: $salinity_ppm,
                    co2_storage_capacity_mt: $co2_storage_capacity_mt,
                    latitude: $latitude,
                    longitude: $longitude,
                    cluster_id: $cluster_id
                })
                CREATE (r:RiskAssessment {
                    risk_level: $risk_level,
                    seismic_risk: $seismic_risk,
                    regulatory_score: $regulatory_score
                })
                CREATE (a)-[:LOCATED_IN]->(b)
                CREATE (a)-[:HAS_RISK]->(r)
            """, {**aquifer, **risk})

            if (i + 1) % 10 == 0:
                print(f"  Created {i + 1}/{aquifer_count} aquifers")

        # Verify data
        result = session.run("MATCH (a:Aquifer) RETURN count(a) as count")
        count = result.single()["count"]
        print(f"\nSeeding complete! Created {count} aquifers.")

        # Show sample
        print("\nSample query - Top 5 by capacity:")
        sample = session.run("""
            MATCH (a:Aquifer)-[:LOCATED_IN]->(b:Basin)-[:WITHIN]->(c:Country)
            OPTIONAL MATCH (a)-[:HAS_RISK]->(r:RiskAssessment)
            RETURN a.name as name, a.co2_storage_capacity_mt as capacity,
                   b.name as basin, c.name as country, r.risk_level as risk
            ORDER BY capacity DESC
            LIMIT 5
        """)
        for record in sample:
            print(f"  {record['name']}: {record['capacity']} Mt ({record['basin']}, {record['risk']})")

    driver.close()
    print("\nDone!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Neo4j with aquifer data")
    parser.add_argument("--uri", required=True, help="Neo4j URI (bolt:// or neo4j+s://)")
    parser.add_argument("--user", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", required=True, help="Neo4j password")
    parser.add_argument("--count", type=int, default=50, help="Number of aquifers to create")

    args = parser.parse_args()
    seed_database(args.uri, args.user, args.password, args.count)
```

---

## Task 3.3: Terraform Infrastructure

```hcl
# infrastructure/terraform/main.tf

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AquiferAI"
      Environment = "golden-hour"
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "aws_region" {
  default = "us-east-1"
}

variable "neo4j_uri" {
  description = "Neo4j AuraDB connection URI"
  sensitive   = true
}

variable "neo4j_password" {
  description = "Neo4j AuraDB password"
  sensitive   = true
}

# VPC (use default for cost savings in Golden Hour)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ECR Repository for Backend
resource "aws_ecr_repository" "backend" {
  name                 = "aquifer-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Easy cleanup

  image_scanning_configuration {
    scan_on_push = false  # Skip for speed
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "aquifer-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"  # Cost savings
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/aquifer-backend"
  retention_in_days = 1  # Minimal retention for Golden Hour
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "aquifer-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for Bedrock access)
resource "aws_iam_role" "ecs_task" {
  name = "aquifer-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_access" {
  name = "bedrock-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
      Resource = [
        "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-*",
        "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-haiku-*"
      ]
    }]
  })
}

# Security Group
resource "aws_security_group" "backend" {
  name        = "aquifer-backend-sg"
  description = "Security group for AquiferAI backend"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "aquifer-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"   # 0.5 vCPU - minimal for Golden Hour
  memory                   = "1024"  # 1 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "backend"
    image = "${aws_ecr_repository.backend.repository_url}:latest"

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "LLM_PROVIDER", value = "bedrock" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "NEO4J_URI", value = var.neo4j_uri },
      { name = "NEO4J_USER", value = "neo4j" },
    ]

    secrets = [
      {
        name      = "NEO4J_PASSWORD"
        valueFrom = aws_ssm_parameter.neo4j_password.arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

# SSM Parameter for Neo4j Password
resource "aws_ssm_parameter" "neo4j_password" {
  name  = "/aquifer/neo4j-password"
  type  = "SecureString"
  value = var.neo4j_password
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "aquifer-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = true  # Required for Fargate in default VPC
  }

  # No load balancer for Golden Hour - direct task IP access
}

# Outputs
output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend.name
}
```

```hcl
# infrastructure/terraform/variables.tf

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "neo4j_uri" {
  description = "Neo4j AuraDB connection URI"
  type        = string
  sensitive   = true
}

variable "neo4j_password" {
  description = "Neo4j AuraDB password"
  type        = string
  sensitive   = true
}
```

```hcl
# infrastructure/terraform/outputs.tf

output "backend_ecr_url" {
  description = "ECR repository URL for backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.backend.name
}

output "log_group" {
  description = "CloudWatch log group"
  value       = aws_cloudwatch_log_group.backend.name
}

output "instructions" {
  value = <<-EOT

    === GOLDEN HOUR DEPLOYMENT ===

    1. Push Docker image:
       aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}
       docker build -t aquifer-backend ./backend
       docker tag aquifer-backend:latest ${aws_ecr_repository.backend.repository_url}:latest
       docker push ${aws_ecr_repository.backend.repository_url}:latest

    2. Get task IP:
       aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name} --service-name ${aws_ecs_service.backend.name}
       aws ecs describe-tasks --cluster ${aws_ecs_cluster.main.name} --tasks <task-arn>

    3. Access API:
       curl http://<task-public-ip>:8000/health

    4. TEARDOWN (after 2 hours):
       terraform destroy -auto-approve

  EOT
}
```

### Definition of Done (Phase 3)
- [ ] Docker images build successfully
- [ ] docker-compose.prod.yml works locally
- [ ] Seeding script populates 50 aquifers in <30 seconds
- [ ] Terraform plan shows expected resources
- [ ] Estimated cost validated (<$5 for 2 hours)

### Zero-Cost Workarounds (Phase 3)

| Challenge | Workaround |
|-----------|------------|
| Neo4j AuraDB paid | Use **AuraDB Free Tier** (50k nodes, 175k rels) |
| RDS PostgreSQL | Skip for Golden Hour, use SQLite in container |
| ALB ($16/month) | Direct task IP access (no ALB) |
| NAT Gateway | Use default VPC with public subnets |
| CloudFront | Skip for Golden Hour, serve frontend locally |

---

# Phase 4: The "Golden Hour" Deployment (AWS)

## Objective
Execute a 2-hour deployment to capture production metrics for documentation.

## Duration
2 hours (strictly timed)

---

## Pre-Deployment Checklist (Day Before)

```markdown
## Golden Hour Prep Checklist

### AWS Account
- [ ] AWS CLI configured with credentials
- [ ] Bedrock model access enabled for Claude 3.5 Sonnet/Haiku
- [ ] Sufficient credits/budget (~$10)

### Neo4j AuraDB
- [ ] Free tier instance created (or trial activated)
- [ ] Connection URI noted
- [ ] Password saved securely

### Local
- [ ] Docker images built and tested
- [ ] Terraform validated (`terraform validate`)
- [ ] Seeding script tested locally
- [ ] Test queries prepared (10 queries for metrics)

### Recording
- [ ] Screen recording software ready (OBS/Loom)
- [ ] Browser dev tools open (Network tab)
- [ ] Metrics spreadsheet prepared
```

---

## Deployment Script

```bash
#!/bin/bash
# scripts/golden-hour-deploy.sh

set -e

echo "==================================="
echo "  AQUIFER AI - GOLDEN HOUR DEPLOY"
echo "==================================="
echo ""
echo "Start Time: $(date)"
echo ""

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
NEO4J_URI="${NEO4J_URI}"
NEO4J_PASSWORD="${NEO4J_PASSWORD}"

if [ -z "$NEO4J_URI" ] || [ -z "$NEO4J_PASSWORD" ]; then
    echo "ERROR: NEO4J_URI and NEO4J_PASSWORD must be set"
    exit 1
fi

# Step 1: Seed Neo4j AuraDB
echo "[1/5] Seeding Neo4j AuraDB..."
cd infrastructure/seed-data
python seed_neo4j.py \
    --uri "$NEO4J_URI" \
    --password "$NEO4J_PASSWORD" \
    --count 50
cd ../..
echo "✓ Neo4j seeded"
echo ""

# Step 2: Apply Terraform
echo "[2/5] Applying Terraform..."
cd infrastructure/terraform
terraform init
terraform apply -auto-approve \
    -var="aws_region=$AWS_REGION" \
    -var="neo4j_uri=$NEO4J_URI" \
    -var="neo4j_password=$NEO4J_PASSWORD"

ECR_URL=$(terraform output -raw backend_ecr_url)
CLUSTER_NAME=$(terraform output -raw cluster_name)
SERVICE_NAME=$(terraform output -raw service_name)
cd ../..
echo "✓ Infrastructure created"
echo ""

# Step 3: Build and push Docker image
echo "[3/5] Building and pushing Docker image..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

docker build -t aquifer-backend ./backend
docker tag aquifer-backend:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest
echo "✓ Docker image pushed"
echo ""

# Step 4: Force new deployment
echo "[4/5] Deploying to ECS..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment \
    --region $AWS_REGION

# Wait for service to stabilize
echo "Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION
echo "✓ Service deployed"
echo ""

# Step 5: Get task IP
echo "[5/5] Getting task public IP..."
TASK_ARN=$(aws ecs list-tasks \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --query 'taskArns[0]' \
    --output text \
    --region $AWS_REGION)

TASK_DETAILS=$(aws ecs describe-tasks \
    --cluster $CLUSTER_NAME \
    --tasks $TASK_ARN \
    --region $AWS_REGION)

ENI_ID=$(echo $TASK_DETAILS | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value')
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
    --network-interface-ids $ENI_ID \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text \
    --region $AWS_REGION)

echo ""
echo "==================================="
echo "  DEPLOYMENT COMPLETE!"
echo "==================================="
echo ""
echo "API URL: http://${PUBLIC_IP}:8000"
echo "Health:  http://${PUBLIC_IP}:8000/health"
echo "Docs:    http://${PUBLIC_IP}:8000/docs"
echo ""
echo "Time: $(date)"
echo ""
echo "Run metrics capture:"
echo "  ./scripts/capture-metrics.sh http://${PUBLIC_IP}:8000"
echo ""
echo "REMEMBER: Teardown after 2 hours!"
echo "  ./scripts/golden-hour-teardown.sh"
```

---

## Metrics Capture Script

```bash
#!/bin/bash
# scripts/capture-metrics.sh

API_URL="${1:-http://localhost:8000}"
OUTPUT_FILE="metrics_$(date +%Y%m%d_%H%M%S).csv"

echo "==================================="
echo "  METRICS CAPTURE"
echo "==================================="
echo ""
echo "API: $API_URL"
echo "Output: $OUTPUT_FILE"
echo ""

# Test queries
QUERIES=(
    "What are the top 5 aquifers by CO2 storage capacity?"
    "Compare aquifers in Amazon Basin vs Parnaiba Basin"
    "Which low-risk aquifers have capacity greater than 500 Mt?"
    "Show me the average porosity by basin"
    "List all aquifers in Brazil with their risk levels"
    "What is the total CO2 storage capacity of all aquifers?"
    "Find aquifers with depth greater than 2000m and high porosity"
    "Compare risk profiles across different countries"
    "Which cluster has the highest average capacity?"
    "Recommend the best aquifer for CO2 storage in South America"
)

# CSV header
echo "timestamp,query_num,query,response_time_ms,success,retry_count,token_estimate" > $OUTPUT_FILE

for i in "${!QUERIES[@]}"; do
    QUERY="${QUERIES[$i]}"
    echo "[$((i+1))/${#QUERIES[@]}] Testing: ${QUERY:0:50}..."

    START_TIME=$(date +%s%3N)

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_URL/api/v2/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$QUERY\", \"expert_mode\": true}")

    END_TIME=$(date +%s%3N)
    RESPONSE_TIME=$((END_TIME - START_TIME))

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" == "200" ]; then
        SUCCESS="true"
        RETRY_COUNT=$(echo "$BODY" | jq -r '.execution_trace.total_retries // 0')
        # Rough token estimate (4 chars per token)
        TOKEN_EST=$((${#BODY} / 4))
    else
        SUCCESS="false"
        RETRY_COUNT="0"
        TOKEN_EST="0"
    fi

    TIMESTAMP=$(date -Iseconds)
    echo "$TIMESTAMP,$((i+1)),\"${QUERY}\",${RESPONSE_TIME},$SUCCESS,$RETRY_COUNT,$TOKEN_EST" >> $OUTPUT_FILE

    # Brief pause between requests
    sleep 2
done

echo ""
echo "==================================="
echo "  METRICS SUMMARY"
echo "==================================="

# Calculate summary stats
echo ""
echo "Results saved to: $OUTPUT_FILE"
echo ""

# Parse and summarize
awk -F',' 'NR>1 {
    total+=$4;
    count++;
    if($5=="true") success++;
    retries+=$6
}
END {
    print "Total Queries: " count
    print "Successful: " success " (" int(success/count*100) "%)"
    print "Average Response Time: " int(total/count) "ms"
    print "Total Self-Healing Retries: " retries
}' $OUTPUT_FILE
```

---

## Teardown Script

```bash
#!/bin/bash
# scripts/golden-hour-teardown.sh

set -e

echo "==================================="
echo "  AQUIFER AI - TEARDOWN"
echo "==================================="
echo ""
echo "WARNING: This will destroy all AWS resources!"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[1/3] Stopping ECS service..."
cd infrastructure/terraform
CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "")
SERVICE_NAME=$(terraform output -raw service_name 2>/dev/null || echo "")

if [ -n "$CLUSTER_NAME" ] && [ -n "$SERVICE_NAME" ]; then
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --desired-count 0 \
        --region ${AWS_REGION:-us-east-1} 2>/dev/null || true
fi

echo "[2/3] Destroying Terraform resources..."
terraform destroy -auto-approve

echo "[3/3] Cleaning up ECR images..."
aws ecr batch-delete-image \
    --repository-name aquifer-backend \
    --image-ids imageTag=latest \
    --region ${AWS_REGION:-us-east-1} 2>/dev/null || true

cd ../..

echo ""
echo "==================================="
echo "  TEARDOWN COMPLETE!"
echo "==================================="
echo ""
echo "Time: $(date)"
echo ""
echo "Estimated cost incurred: ~\$3-5"
echo ""
echo "Don't forget to:"
echo "- [ ] Delete Neo4j AuraDB instance (if trial)"
echo "- [ ] Review AWS Cost Explorer tomorrow"
```

---

## Metrics to Capture Checklist

```markdown
## Golden Hour Metrics Checklist

### Performance Metrics
- [ ] **Response Time (P50, P95, P99)**
  - Simple queries (e.g., "List top 5 aquifers")
  - Complex queries (e.g., "Compare X basin vs Y basin")
  - Analytical queries (e.g., "Risk analysis of...")

- [ ] **Query Success Rate**
  - First-attempt success rate
  - After self-healing success rate
  - Total failures

- [ ] **Self-Healing Stats**
  - Average retries per query
  - Most common error types
  - Healing success rate

### Comparison Metrics (Ollama vs Bedrock)
| Metric | Ollama (Local) | Bedrock (Cloud) | Improvement |
|--------|----------------|-----------------|-------------|
| Avg Response Time | ___ms | ___ms | ___% |
| P95 Response Time | ___ms | ___ms | ___% |
| Query Success Rate | ___% | ___% | ___% |
| Self-Healing Rate | ___% | ___% | ___% |

### Cost Tracking
- [ ] Bedrock token usage (input/output)
- [ ] ECS Fargate compute hours
- [ ] Data transfer (if any)
- [ ] Total AWS cost

### Demo Recording
- [ ] Screen recording of chat interaction
- [ ] Expert Mode query editing demo
- [ ] Execution trace visualization
- [ ] Self-healing in action (intentional error)

### Screenshots for README
- [ ] Main chat interface with response
- [ ] Expert Mode with Cypher query
- [ ] Query editor modal
- [ ] Execution trace timeline
- [ ] Map visualization
- [ ] Architecture in action (optional)
```

---

## Cost Estimate Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GOLDEN HOUR COST ESTIMATE (2 Hours)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SERVICE                          USAGE              COST                   │
│  ─────────────────────────────────────────────────────────────              │
│                                                                              │
│  ECS Fargate                                                                 │
│    0.5 vCPU × 2 hours            1 vCPU-hour        $0.04                   │
│    1 GB RAM × 2 hours            2 GB-hours         $0.01                   │
│                                                                              │
│  Amazon Bedrock                                                              │
│    Claude 3.5 Sonnet                                                         │
│      ~10 queries × ~2k tokens    20k input tokens   $0.06                   │
│      ~10 queries × ~1k tokens    10k output tokens  $0.15                   │
│    Claude 3.5 Haiku                                                          │
│      ~30 calls × ~500 tokens     15k input tokens   $0.01                   │
│      ~30 calls × ~200 tokens     6k output tokens   $0.01                   │
│                                                                              │
│  ECR Storage                      ~500MB image       $0.05                   │
│                                                                              │
│  CloudWatch Logs                  <1 GB              $0.00                   │
│                                                                              │
│  Data Transfer                    Minimal            $0.00                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────              │
│  SUBTOTAL                                            ~$0.33                  │
│                                                                              │
│  Neo4j AuraDB (Free Tier)                            $0.00                   │
│                                                                              │
│  ─────────────────────────────────────────────────────────────              │
│  ESTIMATED TOTAL                                     ~$0.50                  │
│                                                                              │
│  Buffer for extended testing                         +$2.00                  │
│  ─────────────────────────────────────────────────────────────              │
│  BUDGET ALLOCATION                                   $5.00                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Definition of Done (Phase 4)

- [ ] Terraform apply completes without errors
- [ ] ECS service shows "RUNNING" status
- [ ] Health endpoint responds with 200
- [ ] 10 test queries executed successfully
- [ ] Metrics CSV generated with all data points
- [ ] Ollama vs Bedrock comparison table filled
- [ ] Demo video recorded (3-5 minutes)
- [ ] Screenshots captured for README
- [ ] Terraform destroy completes without errors
- [ ] AWS Cost Explorer shows <$5 charge

---

## Post-Golden Hour Tasks

```markdown
### Immediate (Same Day)
- [ ] Commit metrics CSV to repo
- [ ] Update README with comparison table
- [ ] Add screenshots to docs/images/
- [ ] Upload demo video to YouTube/Loom

### Next Day
- [ ] Verify AWS cost in Cost Explorer
- [ ] Delete any lingering resources
- [ ] Write "Lessons Learned" section
- [ ] Final README polish

### Portfolio Enhancement
- [ ] LinkedIn post with demo GIF
- [ ] Add to personal portfolio site
- [ ] GitHub repo description update
```

---

**Document End**

*This roadmap provides a complete implementation path from local development to production-quality metrics capture, all within a $0-10 budget constraint.*
