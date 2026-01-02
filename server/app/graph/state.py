"""
LangGraph State Definitions for AquiferAI V2.0

This module defines all Pydantic models and TypedDict structures used
by the multi-agent workflow for state management and data flow.
"""

from typing import List, Dict, Any, Optional, Literal, TypedDict, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from langgraph.graph import add_messages


# ============================================
# Enums for Classification
# ============================================

class QueryComplexity(str, Enum):
    """Classification of query complexity by the Planner agent."""
    SIMPLE = "SIMPLE"           # Single straightforward query
    COMPOUND = "COMPOUND"       # Multiple related queries
    ANALYTICAL = "ANALYTICAL"   # Requires analysis and synthesis


class ValidationStatus(str, Enum):
    """Status of Cypher query validation."""
    VALID = "VALID"             # Query is valid and executed successfully
    SYNTAX_ERROR = "SYNTAX_ERROR"  # Syntax issues detected
    EXECUTION_ERROR = "EXECUTION_ERROR"  # Query failed during execution
    SCHEMA_ERROR = "SCHEMA_ERROR"  # Schema mismatch (wrong labels/relationships)
    TIMEOUT = "TIMEOUT"         # Query execution timed out
    HEALED = "HEALED"           # Query was fixed by self-healing


# ============================================
# Agent Output Models (Pydantic)
# ============================================

class SubTask(BaseModel):
    """
    Individual sub-task from query decomposition.

    Used by the Planner agent to break down complex queries into
    manageable pieces.
    """
    id: int = Field(description="Sequential ID of the sub-task")
    description: str = Field(description="What this sub-task needs to accomplish")
    dependencies: List[int] = Field(
        default_factory=list,
        description="IDs of sub-tasks that must complete before this one"
    )
    expected_output: str = Field(description="Expected type of result (e.g., 'list of aquifers', 'count')")


class QueryPlan(BaseModel):
    """
    Output from the Planner agent.

    Contains the query complexity classification and decomposition
    into sub-tasks.
    """
    complexity: QueryComplexity = Field(description="Classified complexity level")
    subtasks: List[SubTask] = Field(description="List of sub-tasks to execute")
    reasoning: str = Field(description="Explanation of the planning decision")
    estimated_execution_time: float = Field(
        default=5.0,
        description="Estimated time in seconds to complete all tasks"
    )


class CypherQuery(BaseModel):
    """
    Generated Cypher query from the Cypher Specialist agent.

    Each sub-task gets translated into a Cypher query.
    """
    subtask_id: int = Field(description="ID of the sub-task this query addresses")
    cypher: str = Field(description="The generated Cypher query")
    explanation: str = Field(description="Plain English explanation of what the query does")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the Cypher query (for parameterized queries)"
    )
    expected_columns: List[str] = Field(
        default_factory=list,
        description="Expected column names in the result"
    )


class ValidationResult(BaseModel):
    """
    Result from the Validator agent.

    Contains execution results, errors, and self-healing information.
    """
    subtask_id: int = Field(description="ID of the sub-task")
    status: ValidationStatus = Field(description="Validation status")
    original_query: str = Field(description="The original Cypher query")
    healed_query: Optional[str] = Field(
        default=None,
        description="The healed query (if self-healing was applied)"
    )
    results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Query results if successful"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if validation failed"
    )
    retry_count: int = Field(
        default=0,
        description="Number of self-healing retries performed"
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Query execution time in milliseconds"
    )
    healing_explanation: Optional[str] = Field(
        default=None,
        description="Explanation of what was fixed during self-healing"
    )


class Insight(BaseModel):
    """Individual insight from data analysis."""
    title: str = Field(description="Short title for the insight")
    description: str = Field(description="Detailed explanation")
    importance: Literal["high", "medium", "low"] = Field(description="Importance level")


class Recommendation(BaseModel):
    """Actionable recommendation for the user."""
    action: str = Field(description="Recommended action to take")
    rationale: str = Field(description="Why this is recommended")
    priority: Literal["high", "medium", "low"] = Field(description="Priority level")


class VisualizationHint(BaseModel):
    """Hint for frontend visualization."""
    type: Literal["table", "map", "chart", "stats"] = Field(description="Type of visualization")
    data_key: str = Field(description="Key to access relevant data in the response")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration options for the visualization"
    )


class AnalysisReport(BaseModel):
    """
    Output from the Analyst agent.

    Synthesizes all results into actionable insights and recommendations.
    """
    summary: str = Field(description="High-level summary of findings")
    insights: List[Insight] = Field(
        default_factory=list,
        description="Key insights extracted from the data"
    )
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Actionable recommendations for the user"
    )
    data_quality_notes: Optional[str] = Field(
        default=None,
        description="Notes about data quality or limitations"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions for deeper analysis"
    )
    visualization_hints: List[VisualizationHint] = Field(
        default_factory=list,
        description="Hints for frontend visualization"
    )


class ExecutionTraceStep(BaseModel):
    """Single step in the execution trace for Expert Mode."""
    agent: str = Field(description="Name of the agent that executed this step")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input: Dict[str, Any] = Field(description="Input to the agent")
    output: Dict[str, Any] = Field(description="Output from the agent")
    duration_ms: float = Field(description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error if step failed")


# ============================================
# Agent State (TypedDict for LangGraph)
# ============================================

class AgentState(TypedDict):
    """
    Shared state across all agents in the LangGraph workflow.

    This state is passed between nodes and updated as the workflow progresses.
    LangGraph uses TypedDict for state management with type hints.
    """

    # ==================== Input Fields ====================
    user_query: str
    """Original user query"""

    session_id: Optional[str]
    """Chat session ID for conversation history"""

    expert_mode: bool
    """If True, return detailed execution trace and query info"""

    # ==================== Conversation History ====================
    messages: Annotated[List[Dict[str, str]], add_messages]
    """Conversation messages with LangGraph's add_messages reducer"""

    # ==================== Agent Outputs ====================
    query_plan: Optional[QueryPlan]
    """Output from Planner agent"""

    generated_queries: Optional[List[CypherQuery]]
    """Output from Cypher Specialist agent"""

    validation_results: Optional[List[ValidationResult]]
    """Output from Validator agent"""

    analysis_report: Optional[AnalysisReport]
    """Output from Analyst agent"""

    # ==================== Control Flow ====================
    error_count: int
    """Number of errors encountered"""

    should_escalate: bool
    """If True, escalate to human or provide fallback response"""

    all_queries_valid: bool
    """If True, all queries validated successfully"""

    total_retries: int
    """Total number of self-healing retries across all queries"""

    max_retries_exceeded: bool
    """If True, max retries reached for at least one query"""

    # ==================== Final Output ====================
    final_response: Optional[str]
    """Final markdown-formatted response to the user"""

    execution_trace: Optional[List[ExecutionTraceStep]]
    """Detailed execution trace for Expert Mode"""

    # ==================== Metadata ====================
    neo4j_schema: Optional[Dict[str, Any]]
    """Cached Neo4j schema for agents"""

    start_time: Optional[datetime]
    """Workflow start time for performance tracking"""

    end_time: Optional[datetime]
    """Workflow end time for performance tracking"""


# ============================================
# Helper Functions
# ============================================

def create_initial_state(
    user_query: str,
    session_id: Optional[str] = None,
    expert_mode: bool = False,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> AgentState:
    """
    Create an initial state for the workflow.

    Args:
        user_query: The user's question
        session_id: Optional session ID for chat history
        expert_mode: Enable detailed execution trace
        conversation_history: Previous messages in the conversation

    Returns:
        Initial AgentState ready for the workflow
    """
    return AgentState(
        # Input
        user_query=user_query,
        session_id=session_id,
        expert_mode=expert_mode,

        # Conversation
        messages=conversation_history or [],

        # Agent outputs (None initially)
        query_plan=None,
        generated_queries=None,
        validation_results=None,
        analysis_report=None,

        # Control flow
        error_count=0,
        should_escalate=False,
        all_queries_valid=False,
        total_retries=0,
        max_retries_exceeded=False,

        # Final output
        final_response=None,
        execution_trace=[] if expert_mode else None,

        # Metadata
        neo4j_schema=None,
        start_time=datetime.utcnow(),
        end_time=None
    )


def add_trace_step(
    state: AgentState,
    agent: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    duration_ms: float,
    error: Optional[str] = None
) -> AgentState:
    """
    Add a step to the execution trace (if expert mode is enabled).

    Args:
        state: Current agent state
        agent: Name of the agent
        input_data: Input to the agent
        output_data: Output from the agent
        duration_ms: Execution time
        error: Error message if failed

    Returns:
        Updated state with new trace step
    """
    if state.get("expert_mode") and state.get("execution_trace") is not None:
        trace_step = ExecutionTraceStep(
            agent=agent,
            timestamp=datetime.utcnow(),
            input=input_data,
            output=output_data,
            duration_ms=duration_ms,
            error=error
        )
        state["execution_trace"].append(trace_step)

    return state
