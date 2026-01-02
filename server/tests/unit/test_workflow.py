"""
Unit tests for LangGraph workflow.

Tests the workflow structure, state management, and routing logic.

Usage:
    # From server/ directory
    python tests/unit/test_workflow.py
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.graph.workflow import create_workflow, execute_workflow
from app.graph.state import create_initial_state, QueryComplexity, ValidationStatus


async def test_workflow_structure():
    """Test that workflow has all required nodes and edges."""
    print("\n" + "="*60)
    print("TEST 1: Workflow Structure")
    print("="*60)

    try:
        workflow = create_workflow()

        # Check nodes exist
        nodes = workflow.nodes
        required_nodes = ["plan", "generate_cypher", "validate", "analyze", "format_response", "handle_error"]

        print(f"✓ Workflow nodes: {list(nodes.keys())}")

        for node_name in required_nodes:
            if node_name in nodes:
                print(f"  ✓ Node '{node_name}' exists")
            else:
                print(f"  ✗ Node '{node_name}' missing")
                return False

        print(f"\n✓ All {len(required_nodes)} required nodes present")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_state_creation():
    """Test initial state creation."""
    print("\n" + "="*60)
    print("TEST 2: State Creation")
    print("="*60)

    try:
        state = create_initial_state(
            user_query="Test query",
            session_id="test-session",
            expert_mode=True
        )

        # Check required fields
        assert state["user_query"] == "Test query"
        assert state["session_id"] == "test-session"
        assert state["expert_mode"] is True
        assert state["error_count"] == 0
        assert state["all_queries_valid"] is False
        assert state["execution_trace"] == []

        print("✓ Initial state created correctly")
        print(f"  - user_query: {state['user_query']}")
        print(f"  - session_id: {state['session_id']}")
        print(f"  - expert_mode: {state['expert_mode']}")
        print(f"  - error_count: {state['error_count']}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_workflow_execution():
    """Test end-to-end workflow execution with stub agents."""
    print("\n" + "="*60)
    print("TEST 3: Workflow Execution (Stub Agents)")
    print("="*60)

    try:
        print("Executing workflow with stub agents...")

        final_state = await execute_workflow(
            user_query="Test query: List aquifers",
            session_id="test-123",
            expert_mode=True
        )

        # Check final state has expected outputs
        print("\n✓ Workflow completed successfully")
        print(f"  - Query plan created: {final_state.get('query_plan') is not None}")
        print(f"  - Queries generated: {final_state.get('generated_queries') is not None}")
        print(f"  - Validation results: {final_state.get('validation_results') is not None}")
        print(f"  - Analysis report: {final_state.get('analysis_report') is not None}")
        print(f"  - Final response: {final_state.get('final_response') is not None}")

        # Check response content
        if final_state.get("final_response"):
            response = final_state["final_response"]
            print(f"\n✓ Response generated ({len(response)} characters)")
            print(f"\nFirst 200 chars of response:")
            print(f"{response[:200]}...")

        # Check expert mode details
        if final_state.get("expert_mode"):
            print(f"\n✓ Expert mode enabled")
            if "Generated Cypher Queries:" in final_state.get("final_response", ""):
                print(f"  ✓ Cypher queries included in response")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pydantic_models():
    """Test Pydantic model validation."""
    print("\n" + "="*60)
    print("TEST 4: Pydantic Model Validation")
    print("="*60)

    try:
        from app.graph.state import (
            QueryPlan, SubTask, CypherQuery,
            ValidationResult, AnalysisReport,
            Insight, Recommendation
        )

        # Test SubTask
        subtask = SubTask(
            id=1,
            description="Test task",
            dependencies=[],
            expected_output="data"
        )
        print("✓ SubTask model validated")

        # Test QueryPlan
        plan = QueryPlan(
            complexity=QueryComplexity.SIMPLE,
            subtasks=[subtask],
            reasoning="Test reasoning",
            estimated_execution_time=5.0
        )
        print("✓ QueryPlan model validated")

        # Test CypherQuery
        cypher = CypherQuery(
            subtask_id=1,
            cypher="MATCH (a:Aquifer) RETURN a",
            explanation="Test query",
            parameters={},
            expected_columns=["a"]
        )
        print("✓ CypherQuery model validated")

        # Test ValidationResult
        validation = ValidationResult(
            subtask_id=1,
            status=ValidationStatus.VALID,
            original_query="MATCH (a) RETURN a",
            results=[{"a": "test"}],
            execution_time_ms=100.0
        )
        print("✓ ValidationResult model validated")

        # Test AnalysisReport
        report = AnalysisReport(
            summary="Test summary",
            insights=[
                Insight(
                    title="Test insight",
                    description="Description",
                    importance="high"
                )
            ],
            recommendations=[
                Recommendation(
                    action="Test action",
                    rationale="Rationale",
                    priority="medium"
                )
            ]
        )
        print("✓ AnalysisReport model validated")

        print("\n✓ All Pydantic models validated successfully")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LANGGRAPH WORKFLOW TEST SUITE")
    print("="*60)

    results = []

    # Test 1: Workflow structure
    results.append(await test_workflow_structure())

    # Test 2: State creation
    results.append(await test_state_creation())

    # Test 3: Pydantic models
    results.append(await test_pydantic_models())

    # Test 4: Workflow execution
    results.append(await test_workflow_execution())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Task 1.2 is complete.")
        print("\nNext: Implement agent nodes in Task 1.3")
    else:
        print(f"\n✗ {total - passed} test(s) failed.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
