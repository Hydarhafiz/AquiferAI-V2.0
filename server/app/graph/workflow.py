"""
LangGraph Workflow Definition for AquiferAI V2.0

This module defines the multi-agent workflow orchestration using LangGraph.
The workflow coordinates between Planner, Cypher Specialist, Validator, and Analyst agents.
"""

import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState, add_trace_step

# Import real agent implementations (Task 1.3 complete)
from app.agents.planner import plan_node
from app.agents.cypher_specialist import generate_cypher_node
from app.agents.validator import validate_node
from app.agents.analyst import analyze_node

logger = logging.getLogger(__name__)


# ============================================
# Helper Node Functions
# ============================================

# Note: Agent node functions (plan_node, generate_cypher_node, validate_node, analyze_node)
# are now imported from app.agents package (implemented in Task 1.3)


async def format_response_node(state: AgentState) -> AgentState:
    """
    Format the final response for the user.

    Converts the analysis report into a markdown-formatted response.
    In expert mode, includes execution trace and query details.
    """
    logger.info("[FORMAT] Formatting final response")

    report = state.get("analysis_report")
    if not report:
        state["final_response"] = "I encountered an error processing your request. Please try again."
        return state

    # Build markdown response
    response_parts = []

    # Summary
    response_parts.append(f"**Summary:**\n{report.summary}\n")

    # Insights
    if report.insights:
        response_parts.append("\n**Key Insights:**")
        for i, insight in enumerate(report.insights, 1):
            importance_emoji = "🔴" if insight.importance == "high" else "🟡" if insight.importance == "medium" else "🟢"
            response_parts.append(f"{i}. {importance_emoji} **{insight.title}**")
            response_parts.append(f"   {insight.description}")

    # Recommendations
    if report.recommendations:
        response_parts.append("\n**Recommendations:**")
        for i, rec in enumerate(report.recommendations, 1):
            priority_emoji = "⚡" if rec.priority == "high" else "📌" if rec.priority == "medium" else "💡"
            response_parts.append(f"{i}. {priority_emoji} {rec.action}")
            response_parts.append(f"   *{rec.rationale}*")

    # Follow-up questions
    if report.follow_up_questions:
        response_parts.append("\n**You might also want to ask:**")
        for question in report.follow_up_questions:
            response_parts.append(f"- {question}")

    # Expert mode: Add execution details
    if state.get("expert_mode"):
        response_parts.append("\n---\n**🔧 Expert Mode Details:**")

        # Query plan
        if state.get("query_plan"):
            plan = state["query_plan"]
            response_parts.append(f"\n**Query Complexity:** {plan.complexity}")
            response_parts.append(f"**Sub-tasks:** {len(plan.subtasks)}")

        # Cypher queries
        if state.get("generated_queries"):
            response_parts.append("\n**Generated Cypher Queries:**")
            for i, query in enumerate(state["generated_queries"], 1):
                response_parts.append(f"\n{i}. `{query.cypher}`")
                response_parts.append(f"   *{query.explanation}*")

        # Validation results
        if state.get("validation_results"):
            response_parts.append("\n**Validation Results:**")
            for result in state["validation_results"]:
                status_emoji = "✅" if result.status.value == "VALID" else "🔄" if result.status.value == "HEALED" else "❌"
                response_parts.append(f"- {status_emoji} {result.status.value} ({result.execution_time_ms:.0f}ms)")
                if result.retry_count > 0:
                    response_parts.append(f"  Self-healing retries: {result.retry_count}")

        # Performance
        if state.get("start_time"):
            duration = (datetime.utcnow() - state["start_time"]).total_seconds()
            response_parts.append(f"\n**Total execution time:** {duration:.2f}s")

    state["final_response"] = "\n".join(response_parts)
    state["end_time"] = datetime.utcnow()

    logger.info("[FORMAT] Response formatted successfully")
    return state


async def handle_error_node(state: AgentState) -> AgentState:
    """
    Handle errors and provide graceful fallback response.

    Called when validation fails or max retries exceeded.
    """
    logger.error("[ERROR] Handling workflow error")

    error_parts = [
        "I encountered some difficulties processing your query. Here's what happened:",
        ""
    ]

    # Check validation results for errors
    if state.get("validation_results"):
        failed_queries = [r for r in state["validation_results"] if r.status.value != "VALID"]
        if failed_queries:
            error_parts.append("**Query Issues:**")
            for result in failed_queries:
                error_parts.append(f"- {result.status.value}: {result.error_message or 'Unknown error'}")
                if result.healing_explanation:
                    error_parts.append(f"  Attempted fix: {result.healing_explanation}")

    # Suggestions
    error_parts.append("\n**Suggestions:**")
    error_parts.append("1. Try rephrasing your question")
    error_parts.append("2. Break complex queries into simpler parts")
    error_parts.append("3. Use Expert Mode to see detailed execution logs")

    # Expert mode: Show attempted queries
    if state.get("expert_mode") and state.get("generated_queries"):
        error_parts.append("\n**🔧 Attempted Queries:**")
        for query in state["generated_queries"]:
            error_parts.append(f"```cypher\n{query.cypher}\n```")

    state["final_response"] = "\n".join(error_parts)
    state["should_escalate"] = True
    state["end_time"] = datetime.utcnow()

    logger.info("[ERROR] Error response generated")
    return state


# ============================================
# Conditional Routing Functions
# ============================================

def route_after_validation(state: AgentState) -> Literal["analyze", "handle_error"]:
    """
    Route after validation based on results.

    If all queries are valid, proceed to analysis.
    If max retries exceeded or critical errors, handle error.
    """
    if state.get("all_queries_valid"):
        logger.info("[ROUTE] All queries valid → proceeding to analysis")
        return "analyze"
    elif state.get("max_retries_exceeded") or state.get("error_count", 0) > 5:
        logger.warning("[ROUTE] Max retries or errors exceeded → error handling")
        return "handle_error"
    else:
        logger.info("[ROUTE] Some queries failed but retries available → analysis with partial data")
        return "analyze"


# ============================================
# Workflow Construction
# ============================================

def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for the multi-agent system.

    Workflow:
        START → plan → generate_cypher → validate → [conditional]
                                                     ├─> analyze → format_response → END
                                                     └─> handle_error → END

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("generate_cypher", generate_cypher_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("format_response", format_response_node)
    workflow.add_node("handle_error", handle_error_node)

    # Set entry point
    workflow.set_entry_point("plan")

    # Define edges
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

    # Final formatting
    workflow.add_edge("analyze", "format_response")
    workflow.add_edge("format_response", END)
    workflow.add_edge("handle_error", END)

    logger.info("Workflow graph constructed successfully")
    return workflow


def compile_workflow(checkpointer=None) -> StateGraph:
    """
    Compile the workflow with optional checkpointer for conversation history.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     Default: MemorySaver() for in-memory persistence.

    Returns:
        Compiled workflow ready for invocation
    """
    workflow = create_workflow()

    # Use MemorySaver by default for conversation persistence
    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled = workflow.compile(checkpointer=checkpointer)

    logger.info("Workflow compiled with checkpointer")
    return compiled


# ============================================
# Workflow Execution Helpers
# ============================================

async def execute_workflow(
    user_query: str,
    session_id: str = None,
    expert_mode: bool = False,
    conversation_history: list = None
) -> AgentState:
    """
    Execute the workflow for a user query.

    Args:
        user_query: The user's question
        session_id: Optional session ID for conversation history
        expert_mode: Enable detailed execution trace
        conversation_history: Previous messages

    Returns:
        Final state after workflow completion
    """
    from app.graph.state import create_initial_state

    # Create initial state
    initial_state = create_initial_state(
        user_query=user_query,
        session_id=session_id,
        expert_mode=expert_mode,
        conversation_history=conversation_history
    )

    # Compile workflow
    app = compile_workflow()

    # Execute workflow
    config = {"configurable": {"thread_id": session_id or "default"}}
    final_state = await app.ainvoke(initial_state, config)

    return final_state
