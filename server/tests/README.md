# AquiferAI V2.0 Test Suite

This directory contains all tests for the AquiferAI V2.0 multi-agent system.

## Directory Structure

```
tests/
├── __init__.py
├── README.md                    # This file
├── setup_ollama.sh             # Setup script for Ollama models
├── unit/                       # Unit tests for individual components
│   ├── __init__.py
│   └── test_llm_provider.py   # LLM provider abstraction tests
└── integration/                # Integration tests (coming in later tasks)
    └── __init__.py
```

## Running Tests

### Unit Tests

#### Test LLM Provider (Task 1.1)

```bash
# From server/ directory
python tests/unit/test_llm_provider.py

# Or with pytest
pytest tests/unit/test_llm_provider.py -v
```

**Prerequisites:**
1. Ollama server running: `ollama serve`
2. Models installed: `./tests/setup_ollama.sh`

### Setup Ollama Models

```bash
# From server/ directory
./tests/setup_ollama.sh
```

This will pull all required models:
- `llama3.2:3b` (~2GB) - Planner & Validator
- `qwen2.5-coder:7b` (~4.7GB) - Cypher Specialist
- `llama3:8b` (~4.7GB) - Analyst

**Total disk space:** ~11.4GB

## Test Coverage by Phase

### Phase 1: The Brain Refactor

- [x] **Task 1.1:** LLM Provider
  - `tests/unit/test_llm_provider.py`

- [ ] **Task 1.2:** LangGraph State & Workflow
  - `tests/unit/test_state.py` (coming soon)
  - `tests/unit/test_workflow.py` (coming soon)

- [ ] **Task 1.3:** Agent Implementations
  - `tests/unit/test_planner.py` (coming soon)
  - `tests/unit/test_cypher_specialist.py` (coming soon)
  - `tests/unit/test_validator.py` (coming soon)
  - `tests/unit/test_analyst.py` (coming soon)

- [ ] **Task 1.4:** Neo4j Service
  - `tests/unit/test_neo4j_service.py` (coming soon)

- [ ] **Task 1.5:** Integration
  - `tests/integration/test_end_to_end.py` (coming soon)
  - `tests/integration/test_self_healing.py` (coming soon)

## Environment Variables

Tests use the same `.env` file as the main application. Key variables:

```bash
LLM_PROVIDER=ollama              # Use Ollama for local tests
OLLAMA_BASE_URL=http://localhost:11434
PLANNER_MODEL=llama3.2:3b
CYPHER_MODEL=qwen2.5-coder:7b
VALIDATOR_MODEL=llama3.2:3b
ANALYST_MODEL=llama3:8b
```

## Continuous Integration

Future GitHub Actions workflow will run:
- Unit tests on every PR
- Integration tests on merge to main
- Full end-to-end tests before deployment

## Test Data

Test data and fixtures will be added as we build out the system:
- Mock Neo4j responses
- Sample aquifer data
- Golden query test cases
- Expected Cypher queries

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Make sure you're running tests from the `server/` directory:
```bash
cd server
python tests/unit/test_llm_provider.py
```

### "Ollama server not responding"

Start the Ollama service:
```bash
ollama serve
```

### "Model not found"

Pull the required models:
```bash
./tests/setup_ollama.sh
```

## Contributing

When adding new tests:
1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Follow the naming convention: `test_<component>.py`
4. Update this README with the new test file
5. Ensure tests can run independently
