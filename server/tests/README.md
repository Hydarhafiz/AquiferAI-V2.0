# AquiferAI V2.0 Test Suite

This directory contains all tests for the AquiferAI V2.0 multi-agent system, organized by implementation phase.

## Directory Structure

```
tests/
├── __init__.py
├── README.md                           # This file
├── conftest.py                         # Shared test configuration & logging
├── setup_ollama.sh                     # Setup script for Ollama models
├── scripts/
│   └── seed_neo4j.py                   # Database seeding script
├── unit/
│   ├── __init__.py
│   ├── phase1/                         # Phase 1 unit tests
│   │   ├── __init__.py
│   │   ├── test_llm_provider.py        # LLM provider abstraction
│   │   ├── test_workflow.py            # LangGraph workflow
│   │   ├── test_agents.py              # All 4 agents
│   │   └── test_neo4j_service.py       # Neo4j service
│   └── phase2/                         # Phase 2 unit tests
│       ├── __init__.py
│       └── (future tests)
├── integration/
│   ├── __init__.py
│   ├── phase1/                         # Phase 1 integration tests
│   │   ├── __init__.py
│   │   ├── test_end_to_end.py          # Complete workflow tests
│   │   └── test_api_endpoints.py       # API endpoint tests
│   └── phase2/                         # Phase 2 integration tests
│       ├── __init__.py
│       └── (future tests)
└── logs/
    ├── .gitignore
    ├── phase1/                         # Phase 1 test logs
    │   └── *.log
    └── phase2/                         # Phase 2 test logs
        └── *.log
```

## Running Tests

### Phase 1 Tests

#### Unit Tests

```bash
# From server/ directory
cd server

# Run all Phase 1 unit tests
python -m pytest tests/unit/phase1/ -v

# Run specific test file
python tests/unit/phase1/test_llm_provider.py
python tests/unit/phase1/test_workflow.py
python tests/unit/phase1/test_agents.py
python tests/unit/phase1/test_neo4j_service.py
```

#### Integration Tests

```bash
# Run end-to-end workflow tests
python tests/integration/phase1/test_end_to_end.py

# Run API endpoint tests (requires server running)
uvicorn main:app --reload &
python tests/integration/phase1/test_api_endpoints.py
```

### Phase 2 Tests (Coming Soon)

```bash
# Run Phase 2 unit tests
python -m pytest tests/unit/phase2/ -v

# Run Phase 2 integration tests
python tests/integration/phase2/test_expert_mode.py
```

## Test Logs

Test logs are automatically saved to phase-specific directories:

- **Phase 1 logs:** `tests/logs/phase1/`
- **Phase 2 logs:** `tests/logs/phase2/`

Log files follow the naming convention: `{test_name}_{YYYYMMDD_HHMMSS}.log`

## Prerequisites

### 1. Start Docker Services

```bash
cd server
docker-compose up -d
```

### 2. Seed Neo4j Database

```bash
python tests/scripts/seed_neo4j.py
```

### 3. Setup Ollama Models

```bash
./tests/setup_ollama.sh
```

Required models (~11.4GB total):
- `llama3.2:3b` (~2GB) - Planner & Validator
- `qwen2.5-coder:7b` (~4.7GB) - Cypher Specialist
- `llama3:8b` (~4.7GB) - Analyst

## Test Coverage by Phase

### Phase 1: The Brain Refactor

| Task | Test File | Status |
|------|-----------|--------|
| 1.1 LLM Provider | `unit/phase1/test_llm_provider.py` | COMPLETE |
| 1.2 LangGraph Workflow | `unit/phase1/test_workflow.py` | COMPLETE |
| 1.3 Agent Implementations | `unit/phase1/test_agents.py` | COMPLETE |
| 1.4 Neo4j Service | `unit/phase1/test_neo4j_service.py` | COMPLETE |
| 1.5 Integration | `integration/phase1/test_end_to_end.py` | COMPLETE |
| 1.5 API Endpoints | `integration/phase1/test_api_endpoints.py` | COMPLETE |

### Phase 2: The Expert Interface

| Task | Test File | Status |
|------|-----------|--------|
| 2.1 Expert Mode Toggle | `unit/phase2/test_expert_mode.py` | TODO |
| 2.2 Cypher Query Panel | `integration/phase2/test_query_panel.py` | TODO |
| 2.3 Query Editor Modal | `integration/phase2/test_query_editor.py` | TODO |
| 2.4 Execution Trace | `integration/phase2/test_execution_trace.py` | TODO |
| 2.5 Chat Integration | `integration/phase2/test_chat_expert_mode.py` | TODO |

## Environment Variables

Tests use the same `.env` file as the main application:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
PLANNER_MODEL=llama3.2:3b
CYPHER_MODEL=qwen2.5-coder:7b
VALIDATOR_MODEL=llama3.2:3b
ANALYST_MODEL=llama3:8b

# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=aquifer_password_123
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Run tests from the `server/` directory:
```bash
cd server
python tests/unit/phase1/test_llm_provider.py
```

### "Ollama server not responding"

Start Ollama:
```bash
ollama serve
```

### "Neo4j connection failed"

Start Neo4j container:
```bash
docker-compose up -d neo4j
```

### "No aquifers in database"

Seed the database:
```bash
python tests/scripts/seed_neo4j.py
```

## Adding New Tests

When adding tests for a new phase:

1. Create the phase directory: `tests/{unit,integration}/phaseN/`
2. Add `__init__.py` to the new directory
3. Name test files: `test_<component>.py`
4. Use phase-specific logging:
   ```python
   from tests.conftest import setup_test_logging
   log_file = setup_test_logging("test_name", phase="phaseN")
   ```
5. Update this README with new test files
6. Update the corresponding `PHASEN-TODO.md`

## Continuous Integration

Future GitHub Actions workflow:
- Unit tests run on every PR
- Integration tests run on merge to main
- Full end-to-end tests before deployment
