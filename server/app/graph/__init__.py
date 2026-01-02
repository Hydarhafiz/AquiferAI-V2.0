"""
LangGraph Multi-Agent Workflow for AquiferAI V2.0

This package contains the state definitions and workflow orchestration
for the multi-agent RAG system.
"""

from app.graph.state import (
    AgentState,
    QueryPlan,
    SubTask,
    CypherQuery,
    ValidationResult,
    AnalysisReport,
    QueryComplexity,
    ValidationStatus,
    create_initial_state,
    add_trace_step,
)

from app.graph.workflow import (
    create_workflow,
    compile_workflow,
    execute_workflow,
)

__all__ = [
    # State
    "AgentState",
    "QueryPlan",
    "SubTask",
    "CypherQuery",
    "ValidationResult",
    "AnalysisReport",
    "QueryComplexity",
    "ValidationStatus",
    "create_initial_state",
    "add_trace_step",
    # Workflow
    "create_workflow",
    "compile_workflow",
    "execute_workflow",
]
