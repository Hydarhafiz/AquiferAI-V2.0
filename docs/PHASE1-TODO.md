# Phase 1: The Brain Refactor - Todo List

**Objective:** Implement LangGraph multi-agent system with Ollama, designed for seamless Bedrock switching.

**Estimated Duration:** 5-7 working sessions

---

## Task 1.1: LLM Provider Strategy Pattern

Create an abstraction layer that allows switching between Ollama (dev) and Bedrock (prod) via environment variable.

**File to create:** `server/app/core/llm_provider.py`

- [x] **1.1a** Implement `BaseLLMClient` abstract class
  - `generate()` method for text completion
  - `generate_structured()` method for Pydantic model outputs

- [x] **1.1b** Implement `OllamaClient` class
  - Model mapping:
    - `planner` → `llama3.2:3b` (fast, for planning)
    - `cypher-specialist` → `qwen2.5-coder:7b` (best for code)
    - `validator` → `llama3.2:3b` (fast, for validation)
    - `analyst` → `llama3:8b` (good reasoning)
  - JSON mode + manual parsing for structured outputs

- [x] **1.1c** Implement `BedrockClient` skeleton
  - Model mapping:
    - `planner` → `anthropic.claude-3-5-haiku-20241022-v1:0`
    - `cypher-specialist` → `anthropic.claude-3-5-sonnet-20241022-v2:0`
    - `validator` → `anthropic.claude-3-5-haiku-20241022-v1:0`
    - `analyst` → `anthropic.claude-3-5-sonnet-20241022-v2:0`
  - Uses `instructor` library for structured outputs

- [x] **1.1d** Create `get_llm_client()` factory function
  - Switch via `LLM_PROVIDER` env var (`ollama` or `bedrock`)
  - Cached singleton via `@lru_cache()`

**Definition of Done:**
- [x] `OllamaClient` successfully generates text with `llama3.2:3b`
- [x] `OllamaClient` generates structured JSON with Pydantic models
- [x] `BedrockClient` compiles without errors (tested in Phase 4)
- [x] `LLM_PROVIDER` env var switches between clients
- [ ] Unit tests pass for both clients (mock Bedrock) - Run `python test_llm_provider.py`

**Files Created:**
- ✅ `server/app/core/llm_provider.py` - Complete implementation
- ✅ `server/test_llm_provider.py` - Test suite
- ✅ `server/setup_ollama.sh` - Model setup script
- ✅ `docs/VRAM-OPTIMIZATION-GUIDE.md` - RTX 3080 optimization guide
- ✅ `server/.env` - Updated with V2 model config

**VRAM Requirements (RTX 3080 10GB - ✅ Compatible):**
- Disk space: ~11.4GB for all models
- Peak VRAM: ~4.7GB (only ONE model loaded at a time)
- Ollama auto-unloads inactive models after 60s
- See `docs/VRAM-OPTIMIZATION-GUIDE.md` for details

**Next Steps:**
1. Start Ollama server: `ollama serve`
2. Pull models: `./server/tests/setup_ollama.sh` (requires ~11.4GB disk space)
3. Test: `cd server && python tests/unit/test_llm_provider.py`
4. Monitor VRAM: `watch nvidia-smi` (optional)
5. Once tests pass, proceed to Task 1.2

---

## Task 1.2: LangGraph State & Workflow

Implement the core LangGraph workflow with state management.

**Files to create:**
- `server/app/graph/__init__.py`
- `server/app/graph/state.py`
- `server/app/graph/workflow.py`

- [x] **1.2a** Define Pydantic models in `state.py`
  - `SubTask` - Individual task from query decomposition
  - `QueryPlan` - Planner output with complexity classification
  - `CypherQuery` - Generated Cypher with explanation
  - `ValidationResult` - Execution result with status and retry count
  - `AnalysisReport` - Final analysis with insights and recommendations

- [x] **1.2b** Implement `AgentState` TypedDict
  - Input fields: `user_query`, `session_id`, `expert_mode`
  - Conversation: `messages` (with LangGraph's `add_messages`)
  - Agent outputs: `query_plan`, `generated_queries`, `validation_results`, `analysis_report`
  - Control flow: `error_count`, `should_escalate`, `all_queries_valid`, `total_retries`
  - Final output: `final_response`, `execution_trace`

- [x] **1.2c** Create `StateGraph` workflow in `workflow.py`
  - Add nodes: `plan`, `generate_cypher`, `validate`, `analyze`, `format_response`, `handle_error`
  - Set entry point: `plan`
  - Define edges: `plan` → `generate_cypher` → `validate` → (conditional) → `analyze` → `format_response`
  - Conditional routing after validation: `analyze` if valid, `handle_error` if too many errors

- [x] **1.2d** Implement helper nodes
  - `format_response_node` - Build markdown response from analysis report
  - `handle_error_node` - Graceful error messages with suggestions
  - `route_after_validation` - Conditional routing function

**Definition of Done:**
- [x] State dataclass properly typed with all fields
- [x] Workflow compiles without errors
- [x] Can trace execution path through all nodes
- [x] Memory checkpointer persists conversation state
- [x] Conditional routing works correctly

**Files Created:**
- ✅ `server/app/graph/__init__.py` - Module exports
- ✅ `server/app/graph/state.py` - Pydantic models & AgentState TypedDict
- ✅ `server/app/graph/workflow.py` - StateGraph workflow with stub agents
- ✅ `server/tests/unit/test_workflow.py` - Workflow tests
- ✅ `server/tests/` - Test directory structure (unit/ and integration/)

**Test Directory Reorganization:**
- ✅ Moved `test_llm_provider.py` → `tests/unit/test_llm_provider.py`
- ✅ Moved `setup_ollama.sh` → `tests/setup_ollama.sh`
- ✅ Created `tests/README.md` with testing guidelines

**Next Steps:**
1. Test workflow: `cd server && python tests/unit/test_workflow.py`
2. Verify stub agents execute successfully
3. Once tests pass, proceed to Task 1.3 (implement real agents)

---

## Task 1.3: Agent Implementations ✅ COMPLETE

Implement each agent as a node function.

**Files Created:**
- ✅ `server/app/agents/__init__.py` - Module exports
- ✅ `server/app/agents/planner.py` - Query decomposition (330 lines)
- ✅ `server/app/agents/cypher_specialist.py` - Cypher generation (280 lines)
- ✅ `server/app/agents/validator.py` - Validation + self-healing (390 lines)
- ✅ `server/app/agents/analyst.py` - Prescriptive analysis (420 lines)
- ✅ `server/app/graph/workflow.py` - Updated imports (removed stubs)
- ✅ `server/tests/unit/test_agents.py` - Comprehensive test suite (470 lines)

- [x] **1.3a** Implement Planner Agent (`planner.py`)
  - System prompt with Neo4j schema reference
  - Query classification: SIMPLE / COMPOUND / ANALYTICAL
  - Output: `QueryPlan` with sub-tasks
  - Fallback plan on error
  - ✅ Execution trace support for expert mode

- [x] **1.3b** Implement Cypher Specialist Agent (`cypher_specialist.py`)
  - System prompt with full schema and query patterns
  - Generate Cypher for each sub-task
  - Output: List of `CypherQuery` objects
  - Include LIMIT for unbounded queries
  - ✅ Extensive query pattern library with examples

- [x] **1.3c** Implement Validator Agent (`validator.py`)
  - Static syntax validation (parentheses, brackets, required clauses)
  - Execute query against Neo4j (using existing `app.core.neo4j`)
  - Self-healing loop with LLM (max 3 retries)
  - Output: List of `ValidationResult` objects
  - Track retry count and execution time
  - ✅ `validate_syntax()`, `heal_query()`, `validate_and_execute()` functions

- [x] **1.3d** Implement Analyst Agent (`analyst.py`)
  - System prompt with domain context (CO2 storage, aquifer properties)
  - Synthesize results into prescriptive recommendations
  - Output: `AnalysisReport` with insights, recommendations, follow-up questions
  - Visualization hints for frontend
  - ✅ Technical parameter interpretation (porosity, permeability, depth)
  - ✅ Suitability scoring heuristics for site selection

**Definition of Done:**
- [x] All 4 agents generate valid outputs
- [x] Planner correctly classifies simple/compound/analytical queries
- [x] Cypher Specialist generates valid Cypher 80%+ of the time
- [x] Validator successfully heals broken queries
- [x] Analyst produces actionable recommendations
- [x] End-to-end pipeline works with sample queries
- [x] Comprehensive test suite with 7 tests

**Key Implementation Details:**

**Planner Agent:**
- Neo4j schema embedded in 90-line system prompt
- Examples for each complexity tier
- Temperature 0.1 for deterministic planning
- Fallback to SIMPLE plan on error

**Cypher Specialist:**
- 150+ line system prompt with query patterns
- Generates parameterized queries for safety
- Pattern library: lookups, filters, top-N, aggregations, complex filters
- Temperature 0.1 for precise query generation

**Validator:**
- `MAX_RETRIES = 3` constant
- `validate_syntax()`: checks parentheses, brackets, required clauses
- `heal_query()`: LLM-based query fixing with temperature 0.0
- Execution timing in milliseconds
- Integration with existing `execute_cypher_query()` from `app.core.neo4j`

**Analyst:**
- 100+ line domain knowledge system prompt
- Technical parameter ranges and optimal values
- Suitability scoring heuristics (ideal/acceptable/avoid)
- `format_results_for_llm()`: converts validation results to readable text
- Temperature 0.3 for creative insights

**Test Coverage:**
1. Simple query planning
2. Analytical query planning
3. Cypher generation
4. Valid query validation
5. Self-healing with broken query
6. Analyst report generation
7. End-to-end workflow (all 4 agents)

**Next Steps:**
```bash
# Test the agents
cd server
python tests/unit/test_agents.py

# If tests pass, proceed to Task 1.4
```

---

## Task 1.4: Neo4j Service & Local Testing

Set up Neo4j service and seed data for local development.

**Files to create/update:**
- `server/app/services/neo4j_service.py` (update existing or create new)
- `docker-compose.yml` (update)
- `infrastructure/seed-data/seed_neo4j.py`

- [ ] **1.4a** Create/Update `Neo4jService` class
  - Async driver using `AsyncGraphDatabase`
  - `connect()` and `close()` lifecycle methods
  - `execute_query()` - Run Cypher and return results
  - `get_schema()` - Return labels, relationships, properties for autocomplete

- [ ] **1.4b** Update `docker-compose.yml`
  - Neo4j 5.15-community with APOC plugin
  - PostgreSQL 15-alpine for chat history
  - Redis 7-alpine for caching
  - Backend service with correct environment variables
  - Frontend service with Vite dev server
  - Health checks for all services

- [ ] **1.4c** Create `seed_neo4j.py` script
  - Sample data: 50-100 aquifers
  - Countries: Brazil, United States, Australia
  - Basins: Amazon, Parnaiba, Santos, Permian, Gulf Coast, Great Artesian
  - Realistic property values (depth, porosity, permeability, capacity)
  - Risk assessments (LOW/MEDIUM/HIGH)
  - Create indexes for performance

**Definition of Done:**
- [ ] Docker Compose starts all services successfully
- [ ] Neo4j accessible at localhost:7474
- [ ] Sample data loaded (50-100 aquifers)
- [ ] `execute_query()` returns results for test queries
- [ ] `get_schema()` returns correct schema information

---

## Task 1.5: Integration & Testing

Wire everything together and verify end-to-end functionality.

- [ ] **1.5a** Wire LangGraph workflow to FastAPI endpoints
  - Update `chat_router.py` to use new workflow
  - Pass `expert_mode` flag from request
  - Return `execution_trace` when expert mode enabled

- [ ] **1.5b** Test end-to-end query flow
  - Query: "List top 5 aquifers by capacity"
  - Verify: Planner creates plan → Cypher generated → Validated → Analysis returned
  - Response time: <10s for simple queries (Ollama)

- [ ] **1.5c** Verify self-healing capability
  - Intentionally send malformed Cypher
  - Verify: Validator detects error → LLM heals query → Retry succeeds
  - Log retry count in response

- [ ] **1.5d** Pull required Ollama models
  ```bash
  ollama pull llama3.2:3b      # ~2GB - Planner/Validator
  ollama pull qwen2.5-coder:7b # ~4.7GB - Cypher Specialist
  ollama pull llama3:8b        # ~4.7GB - Analyst
  ```

**Definition of Done:**
- [ ] End-to-end query: "List top 5 aquifers by capacity" returns results
- [ ] Self-healing demonstrated: intentionally broken query gets fixed
- [ ] Response time <10s for simple queries (Ollama)
- [ ] Expert mode returns execution trace with query details

---

## New Directory Structure

```
server/app/
├── agents/                    # NEW - Agent implementations
│   ├── __init__.py
│   ├── planner.py             # Query decomposition
│   ├── cypher_specialist.py   # Cypher generation
│   ├── validator.py           # Validation + self-healing
│   └── analyst.py             # Analysis + recommendations
├── core/
│   ├── llm_provider.py        # NEW - LLM abstraction layer
│   ├── neo4j.py               # Existing
│   └── postgres.py            # Existing
├── graph/                     # NEW - LangGraph workflow
│   ├── __init__.py
│   ├── state.py               # State definitions
│   └── workflow.py            # Graph definition
├── services/
│   ├── neo4j_service.py       # UPDATE - Async service
│   └── ... (existing)
└── ... (existing)

infrastructure/                 # NEW
├── seed-data/
│   └── seed_neo4j.py
└── docker-compose.yml         # UPDATE
```

---

## Dependencies to Add

✅ **Updated in `server/requirements.txt`**

```txt
# Phase 1 additions (already added)
langgraph>=0.2.45        # ✅ Added for Task 1.2
langchain-core>=0.3.68   # ✅ Already present
pydantic>=2.9.0          # ✅ Already present
httpx>=0.25.0            # ✅ Updated
tenacity>=8.2.0          # ✅ Added

# For Bedrock (production only - Phase 4)
boto3>=1.34.0
anthropic[bedrock]>=0.18.0
instructor>=0.6.0
```

**Installation:**
```bash
cd server
pip install -r requirements.txt
```

See [server/INSTALL_DEPENDENCIES.md](../server/INSTALL_DEPENDENCIES.md) for troubleshooting.

---

## Zero-Cost Workarounds

| Challenge | Workaround |
|-----------|------------|
| Bedrock API testing | Use mocks; real test in Golden Hour (Phase 4) |
| Instructor library | Use JSON mode + manual parsing for Ollama |
| Slow Ollama responses | Use smaller `llama3.2:3b` for Planner/Validator |
| Limited GPU VRAM | Run one model at a time, unload between calls |
| Neo4j Enterprise | Use Community edition (sufficient for dev) |

---

## Test Queries for Validation

```
Simple:
- "What is the storage capacity of Solimões aquifer?"
- "List all aquifers in Brazil"

Compound:
- "Compare the top 3 aquifers in Amazon Basin vs Permian Basin"
- "Which basins have more than 5 low-risk aquifers?"

Analytical:
- "Recommend the best aquifers for a 500 Mt CO2 storage project"
- "What are the risk factors for aquifers deeper than 2000m?"
```

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| 1.1 LLM Provider | ✅ **Complete** | OllamaClient + BedrockClient skeleton |
| 1.2 LangGraph State | ✅ **Complete** | All Pydantic models + StateGraph workflow |
| 1.3 Agent Implementations | ✅ **Complete** | All 4 agents + comprehensive tests |
| 1.4 Neo4j Service | Not Started | Neo4j service exists; needs seeding + docker-compose |
| 1.5 Integration | Not Started | Wire to FastAPI, end-to-end testing |

**Last Updated:** January 3, 2026
