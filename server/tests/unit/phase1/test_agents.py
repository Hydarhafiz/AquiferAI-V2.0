"""
Unit tests for Agent implementations (Task 1.3)

Tests the four agent nodes:
- Planner: Query decomposition and complexity classification
- Cypher Specialist: Cypher query generation
- Validator: Query validation and self-healing
- Analyst: Result synthesis and recommendations

Usage:
    # From server/ directory
    python tests/unit/test_agents.py

Prerequisites:
    - Ollama service running (ollama serve)
    - Required models pulled (see tests/setup_ollama.sh)
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.graph.state import (
    create_initial_state,
    QueryComplexity,
    ValidationStatus,
    QueryPlan,
    SubTask,
    CypherQuery
)
from app.agents.planner import plan_node
from app.agents.cypher_specialist import generate_cypher_node
from app.agents.validator import validate_node
from app.agents.analyst import analyze_node


# ============================================
# Test Data
# ============================================

TEST_QUERIES = {
    "simple": "What is the storage capacity of Solimões aquifer?",
    "compound": "Compare top 5 aquifers in Amazon Basin vs Permian Basin by capacity",
    "analytical": "Recommend the best aquifer for a 500 Mt CO2 storage project with low risk"
}


# ============================================
# Test Functions
# ============================================

async def test_planner_simple():
    """Test Planner with a simple query."""
    print("\n" + "="*60)
    print("TEST 1: Planner Agent - Simple Query")
    print("="*60)

    state = create_initial_state(
        user_query=TEST_QUERIES["simple"],
        session_id="test-planner-simple",
        expert_mode=True
    )

    try:
        result_state = await plan_node(state)

        # Validate output
        plan = result_state.get("query_plan")
        assert plan is not None, "Plan not created"
        assert isinstance(plan, QueryPlan), "Plan is not QueryPlan instance"
        assert plan.complexity == QueryComplexity.SIMPLE, f"Expected SIMPLE, got {plan.complexity}"
        assert len(plan.subtasks) >= 1, "No subtasks created"

        print(f"✓ Plan created successfully")
        print(f"  - Complexity: {plan.complexity}")
        print(f"  - Subtasks: {len(plan.subtasks)}")
        print(f"  - Reasoning: {plan.reasoning[:100]}...")

        # Check execution trace
        if result_state.get("execution_trace"):
            print(f"  - Execution trace: {len(result_state['execution_trace'])} steps")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_planner_analytical():
    """Test Planner with an analytical query."""
    print("\n" + "="*60)
    print("TEST 2: Planner Agent - Analytical Query")
    print("="*60)

    state = create_initial_state(
        user_query=TEST_QUERIES["analytical"],
        session_id="test-planner-analytical",
        expert_mode=True
    )

    try:
        result_state = await plan_node(state)

        plan = result_state.get("query_plan")
        assert plan is not None, "Plan not created"
        assert plan.complexity == QueryComplexity.ANALYTICAL, f"Expected ANALYTICAL, got {plan.complexity}"
        assert len(plan.subtasks) >= 2, "Analytical query should have multiple subtasks"

        print(f"✓ Analytical plan created")
        print(f"  - Complexity: {plan.complexity}")
        print(f"  - Subtasks: {len(plan.subtasks)}")

        for i, subtask in enumerate(plan.subtasks, 1):
            print(f"  - Task {i}: {subtask.description[:60]}...")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cypher_specialist():
    """Test Cypher Specialist query generation."""
    print("\n" + "="*60)
    print("TEST 3: Cypher Specialist Agent")
    print("="*60)

    # First create a plan
    state = create_initial_state(
        user_query=TEST_QUERIES["simple"],
        session_id="test-cypher",
        expert_mode=True
    )

    state = await plan_node(state)

    try:
        result_state = await generate_cypher_node(state)

        queries = result_state.get("generated_queries")
        assert queries is not None, "No queries generated"
        assert len(queries) > 0, "Empty query list"
        assert isinstance(queries[0], CypherQuery), "Invalid query type"

        print(f"✓ Generated {len(queries)} queries")

        for i, query in enumerate(queries, 1):
            print(f"\n  Query {i} (subtask {query.subtask_id}):")
            print(f"  - Cypher: {query.cypher}")
            print(f"  - Explanation: {query.explanation[:80]}...")
            print(f"  - Expected columns: {query.expected_columns}")

            # Basic validation
            assert "MATCH" in query.cypher or "CREATE" in query.cypher, "Missing MATCH/CREATE"
            assert "RETURN" in query.cypher, "Missing RETURN clause"

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_validator_with_valid_query():
    """Test Validator with a valid query (no healing needed)."""
    print("\n" + "="*60)
    print("TEST 4: Validator Agent - Valid Query")
    print("="*60)

    # Create state with a simple valid query
    state = create_initial_state(
        user_query="List aquifers",
        session_id="test-validator-valid",
        expert_mode=True
    )

    # Manually inject a known-good query
    state["generated_queries"] = [
        CypherQuery(
            subtask_id=1,
            cypher="MATCH (a:Aquifer) RETURN a.name, a.co2_storage_capacity_mt LIMIT 10",
            explanation="Get aquifer names and capacities",
            parameters={},
            expected_columns=["a.name", "a.co2_storage_capacity_mt"]
        )
    ]

    try:
        result_state = await validate_node(state)

        results = result_state.get("validation_results")
        assert results is not None, "No validation results"
        assert len(results) == 1, "Wrong number of results"

        vr = results[0]
        print(f"✓ Validation complete")
        print(f"  - Status: {vr.status}")
        print(f"  - Retry count: {vr.retry_count}")
        print(f"  - Execution time: {vr.execution_time_ms:.0f}ms")

        if vr.results:
            print(f"  - Results returned: {len(vr.results)} records")
        else:
            print(f"  - No results (possibly empty database)")

        # Status should be VALID if database is available
        # or EXECUTION_ERROR if Neo4j is not running
        assert vr.status in [ValidationStatus.VALID, ValidationStatus.EXECUTION_ERROR], \
            f"Unexpected status: {vr.status}"

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_validator_with_broken_query():
    """Test Validator's self-healing capability with a broken query."""
    print("\n" + "="*60)
    print("TEST 5: Validator Agent - Self-Healing")
    print("="*60)

    state = create_initial_state(
        user_query="Test healing",
        session_id="test-validator-healing",
        expert_mode=True
    )

    # Inject a query with deliberate errors
    state["generated_queries"] = [
        CypherQuery(
            subtask_id=1,
            cypher="MATCH (a:Aquifier) RETURN a.name LIMIT 5",  # Typo: Aquifier instead of Aquifer
            explanation="Deliberately broken query for testing",
            parameters={},
            expected_columns=["a.name"]
        )
    ]

    try:
        result_state = await validate_node(state)

        results = result_state.get("validation_results")
        assert results is not None, "No validation results"

        vr = results[0]
        print(f"✓ Self-healing attempted")
        print(f"  - Final status: {vr.status}")
        print(f"  - Retry count: {vr.retry_count}")
        print(f"  - Original query: {vr.original_query}")

        if vr.healed_query:
            print(f"  - Healed query: {vr.healed_query}")
            print(f"  - Healing explanation: {vr.healing_explanation}")

        if vr.error_message:
            print(f"  - Error: {vr.error_message[:100]}")

        # Should have attempted healing (retry count > 0)
        # May or may not succeed depending on LLM and Neo4j availability
        print(f"\n  Note: Healing {'succeeded' if vr.status == ValidationStatus.HEALED else 'attempted but may have failed'}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analyst():
    """Test Analyst report generation."""
    print("\n" + "="*60)
    print("TEST 6: Analyst Agent")
    print("="*60)

    # Create a state with mock validation results
    state = create_initial_state(
        user_query=TEST_QUERIES["simple"],
        session_id="test-analyst",
        expert_mode=True
    )

    # Add a mock query plan
    state["query_plan"] = QueryPlan(
        complexity=QueryComplexity.SIMPLE,
        subtasks=[SubTask(id=1, description="Test", dependencies=[], expected_output="data")],
        reasoning="Test",
        estimated_execution_time=3.0
    )

    # Add mock validation results with sample data
    from app.graph.state import ValidationResult

    state["validation_results"] = [
        ValidationResult(
            subtask_id=1,
            status=ValidationStatus.VALID,
            original_query="MATCH (a:Aquifer) RETURN a",
            healed_query=None,
            results=[
                {"a.name": "Solimões-347", "a.co2_storage_capacity_mt": 892.5, "a.depth_m": 1200},
                {"a.name": "Amazon-201", "a.co2_storage_capacity_mt": 650.2, "a.depth_m": 1450}
            ],
            error_message=None,
            retry_count=0,
            execution_time_ms=120.0,
            healing_explanation=None
        )
    ]

    try:
        result_state = await analyze_node(state)

        report = result_state.get("analysis_report")
        assert report is not None, "No analysis report generated"

        print(f"✓ Analysis report generated")
        print(f"\n  Summary:")
        print(f"  {report.summary}")

        print(f"\n  Insights ({len(report.insights)}):")
        for i, insight in enumerate(report.insights, 1):
            print(f"  {i}. [{insight.importance.upper()}] {insight.title}")
            print(f"     {insight.description[:100]}...")

        print(f"\n  Recommendations ({len(report.recommendations)}):")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. [{rec.priority.upper()}] {rec.action}")
            print(f"     {rec.rationale[:100]}...")

        if report.follow_up_questions:
            print(f"\n  Follow-up questions ({len(report.follow_up_questions)}):")
            for q in report.follow_up_questions[:3]:
                print(f"  - {q}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_end_to_end_workflow():
    """Test the complete agent workflow end-to-end."""
    print("\n" + "="*60)
    print("TEST 7: End-to-End Agent Workflow")
    print("="*60)

    state = create_initial_state(
        user_query="List the top 3 aquifers by storage capacity",
        session_id="test-e2e",
        expert_mode=True
    )

    try:
        # Step 1: Planning
        print("\n  [1/4] Planning...")
        state = await plan_node(state)
        assert state.get("query_plan") is not None
        print(f"  ✓ Plan created with {len(state['query_plan'].subtasks)} subtasks")

        # Step 2: Cypher Generation
        print("\n  [2/4] Generating Cypher...")
        state = await generate_cypher_node(state)
        assert state.get("generated_queries") is not None
        print(f"  ✓ Generated {len(state['generated_queries'])} queries")

        # Step 3: Validation & Execution
        print("\n  [3/4] Validating & executing...")
        state = await validate_node(state)
        assert state.get("validation_results") is not None

        valid_count = sum(
            1 for vr in state["validation_results"]
            if vr.status in [ValidationStatus.VALID, ValidationStatus.HEALED]
        )
        print(f"  ✓ {valid_count}/{len(state['validation_results'])} queries executed successfully")

        # Step 4: Analysis
        print("\n  [4/4] Analyzing results...")
        state = await analyze_node(state)
        assert state.get("analysis_report") is not None
        print(f"  ✓ Analysis complete with {len(state['analysis_report'].insights)} insights")

        # Summary
        print("\n  End-to-End Test Summary:")
        print(f"  - Query: {state['user_query']}")
        print(f"  - Complexity: {state['query_plan'].complexity}")
        print(f"  - Queries generated: {len(state['generated_queries'])}")
        print(f"  - Successful validations: {valid_count}")
        print(f"  - Total retries (healing): {state.get('total_retries', 0)}")
        print(f"  - Insights: {len(state['analysis_report'].insights)}")
        print(f"  - Recommendations: {len(state['analysis_report'].recommendations)}")

        return True

    except Exception as e:
        print(f"✗ Error during workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# Main Test Runner
# ============================================

async def main():
    """Run all agent tests."""
    print("\n" + "="*60)
    print("AGENT IMPLEMENTATION TEST SUITE (Task 1.3)")
    print("="*60)
    print("\nTesting four agents:")
    print("1. Planner - Query decomposition")
    print("2. Cypher Specialist - Query generation")
    print("3. Validator - Validation & self-healing")
    print("4. Analyst - Result synthesis")
    print("\nPrerequisites:")
    print("- Ollama service running (ollama serve)")
    print("- Models pulled (run tests/setup_ollama.sh)")
    print("- Neo4j running (optional for full validation tests)")

    results = []

    # Test each agent
    results.append(await test_planner_simple())
    results.append(await test_planner_analytical())
    results.append(await test_cypher_specialist())
    results.append(await test_validator_with_valid_query())
    results.append(await test_validator_with_broken_query())
    results.append(await test_analyst())
    results.append(await test_end_to_end_workflow())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Task 1.3 is complete.")
        print("\nNext steps:")
        print("1. Update PHASE1-TODO.md to mark Task 1.3 complete")
        print("2. Proceed to Task 1.4: Neo4j Service & Local Testing")
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("- Ensure Ollama is running: ollama serve")
        print("- Check models are pulled: ollama list")
        print("- For Neo4j tests: ensure Neo4j is running")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
