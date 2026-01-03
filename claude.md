# AquiferAI V2.0 - Claude Code Project Rules

This file contains essential rules and context for Claude Code to follow when working on this project. Read this file at the start of each new conversation to maintain consistency.

## Project Overview

**Project:** AquiferAI V2.0 - Multi-Agent RAG System for Saline Aquifer Analytics
**Stack:** FastAPI + LangGraph + Neo4j + React + TypeScript
**Current Phase:** See `docs/phases/` for latest TODO

## Critical Rules

### 1. Always Follow the Phase TODO

Before starting any work:
1. Read the current phase TODO: `docs/phases/PHASE{N}-TODO.md`
2. Check task status (completed/in-progress/not started)
3. Work only on tasks marked as not started or in-progress
4. Update task status immediately after completion

```bash
# Check current phase
cat docs/phases/PHASE*-TODO.md | grep -A2 "Progress Tracking"
```

### 2. Test-Driven Development

**Every feature must have tests.** No exceptions.

- **Unit tests:** `server/tests/unit/phase{N}/`
- **Integration tests:** `server/tests/integration/phase{N}/`
- **Log location:** `server/tests/logs/phase{N}/`

When creating tests:
```python
# Always use phase-specific logging
from tests.conftest import setup_test_logging
log_file = setup_test_logging("test_name", phase="phase{N}")
```

### 3. Update TODO After Task Completion

After completing any task:
1. Mark task as complete in `PHASE{N}-TODO.md`: `[x]` or `COMPLETE`
2. Add "Files Created/Updated" section if new files added
3. Update "Progress Tracking" table
4. Add "Last Updated" date

Example:
```markdown
- [x] **2.1a** Create Zustand store for Expert Mode state

**Files Created:**
- `client/src/stores/expertModeStore.ts`
```

### 4. Code Organization

Follow the established directory structure:

```
server/
├── app/
│   ├── agents/          # LangGraph agents (Phase 1)
│   ├── api/endpoints/   # FastAPI routes
│   ├── core/            # Core utilities (llm_provider, neo4j)
│   ├── graph/           # LangGraph state & workflow
│   └── services/        # Business logic
├── tests/
│   ├── unit/phase{N}/
│   ├── integration/phase{N}/
│   └── logs/phase{N}/

client/
├── src/
│   ├── components/
│   │   ├── chat/        # Chat UI components
│   │   ├── expert-mode/ # Expert Mode components (Phase 2)
│   │   └── ui/          # Shared UI components
│   ├── stores/          # Zustand stores
│   ├── hooks/           # Custom React hooks
│   └── lib/             # Utilities
```

### 5. API Versioning

All new endpoints use V2 prefix:
- **V2 routes:** `/api/v2/...`
- **V1 routes (legacy):** `/api/...` (do not modify)

### 6. Documentation Requirements

When completing a phase:
1. Create completion report: `docs/reports/PHASE{N}-COMPLETION-REPORT.md`
2. Include test results summary
3. Document any known issues
4. Recommend next steps

### 7. Environment Configuration

**Development:** Uses Ollama for LLM
- `LLM_PROVIDER=ollama`
- Models: llama3.2:3b, qwen2.5-coder:7b, llama3:8b

**Production:** Uses AWS Bedrock
- `LLM_PROVIDER=bedrock`
- Models: Claude 3.5 Haiku, Claude 3.5 Sonnet

### 8. Git Commit Standards

Use conventional commits with co-author:
```
feat(phase1): implement LangGraph workflow

- Add StateGraph with 4 agent nodes
- Implement conditional routing
- Add memory checkpointer

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### 9. Error Handling

- All agents must have fallback behavior
- Validator agent has 3 retry limit for self-healing
- Never expose raw errors to users - use Analyst agent for graceful responses

### 10. Performance Targets

| Query Type | Target Response Time |
|------------|---------------------|
| Simple | <30s |
| Compound | <45s |
| Analytical | <60s |

## Quick Reference

### Key Files to Read First

1. **Current phase TODO:** `docs/phases/PHASE{N}-TODO.md`
2. **Architecture:** `docs/v2-architecture/02-AGENTIC-RAG-SYSTEM-DESIGN.md`
3. **Roadmap:** `docs/v2-architecture/05-IMPLEMENTATION-ROADMAP.md`
4. **Test README:** `server/tests/README.md`

### Common Commands

```bash
# Start services
cd server && docker-compose up -d

# Seed database
python tests/scripts/seed_neo4j.py

# Run Phase 1 tests
python tests/integration/phase1/test_end_to_end.py

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# View recent logs
ls -lt server/tests/logs/phase{N}/ | head -5
```

### Current Status

Check `docs/reports/PHASE{N}-COMPLETION-REPORT.md` for latest status.

---

## Token Optimization Tips

To save tokens in new conversations:

1. **Reference this file first:** "Read claude.md for project context"
2. **Be specific:** "Continue Phase 2 Task 2.3" instead of explaining everything
3. **Use file paths:** Reference files directly instead of describing
4. **Check reports:** Read completion reports for context on completed work

## Phase Summary

| Phase | Name | Status | Key Deliverable |
|-------|------|--------|-----------------|
| 1 | The Brain Refactor | COMPLETE | LangGraph multi-agent workflow |
| 2 | The Expert Interface | TODO | Expert Mode UI components |
| 3 | Cloud Prep | TODO | Terraform, Docker production |
| 4 | Golden Hour | TODO | 2-hour AWS deployment demo |

---

*Last Updated: January 3, 2026*
