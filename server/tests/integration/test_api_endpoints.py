"""
API endpoint tests for V2 chat endpoints.

Tests the FastAPI endpoints to ensure they integrate correctly with the workflow.

Usage:
    # From server/ directory (with FastAPI running)
    python tests/integration/test_api_endpoints.py

    # Or with pytest
    python -m pytest tests/integration/test_api_endpoints.py -v

Prerequisites:
    - FastAPI server running: uvicorn main:app --reload
    - Or use docker-compose: docker-compose up
"""

import asyncio
import sys
import os
import httpx
from pathlib import Path

# Add server directory to path for imports
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

# Configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0  # Increased timeout for LLM operations


async def test_health_check():
    """Test 1: V2 health check endpoint."""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/v2/chat/health")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed")
            print(f"  - Status: {data.get('status')}")
            print(f"  - Version: {data.get('version')}")
            print(f"  - Workflow: {data.get('workflow')}")
            print(f"  - Agents: {', '.join(data.get('agents', []))}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        print("  Make sure the server is running: uvicorn main:app --reload")
        return False


async def test_create_session():
    """Test 2: Create new session."""
    print("\n" + "="*60)
    print("TEST 2: Create Session")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v2/chat/sessions",
                json={"title": "API Test Session"}
            )

        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            print(f"✓ Session created")
            print(f"  - Session ID: {session_id}")
            print(f"  - Title: {data.get('title')}")
            return session_id
        else:
            print(f"✗ Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None


async def test_send_message(session_id: str = None, expert_mode: bool = False):
    """Test 3: Send chat message."""
    print("\n" + "="*60)
    print(f"TEST 3: Send Message (expert_mode={expert_mode})")
    print("="*60)

    try:
        request_data = {
            "message": "List 3 aquifers with high porosity",
            "expert_mode": expert_mode
        }

        if session_id:
            request_data["session_id"] = session_id

        print(f"Sending request:")
        print(f"  - Message: {request_data['message']}")
        print(f"  - Session ID: {session_id or '(new session)'}")
        print(f"  - Expert mode: {expert_mode}")
        print()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v2/chat/message",
                json=request_data
            )

        if response.status_code == 200:
            data = response.json()

            print(f"✓ Message processed successfully")
            print(f"  - Session ID: {data.get('session_id')}")
            print(f"  - Response length: {len(data.get('ai_response', ''))} characters")

            # Print response preview
            ai_response = data.get('ai_response', '')
            print(f"\n  Response preview (first 300 chars):")
            print(f"  {ai_response[:300]}...")

            # Check metadata
            metadata = data.get('metadata')
            if metadata:
                print(f"\n  ✓ Metadata included:")
                print(f"    - Complexity: {metadata.get('complexity')}")
                print(f"    - Queries executed: {metadata.get('queries_executed')}")
                print(f"    - Total retries: {metadata.get('total_retries')}")
                print(f"    - All valid: {metadata.get('all_queries_valid')}")

            # Check execution trace (expert mode)
            execution_trace = data.get('execution_trace')
            if execution_trace:
                print(f"\n  ✓ Execution trace (Expert Mode):")
                for step in execution_trace:
                    print(f"    • {step['agent']}: {step['duration_ms']:.0f}ms ({step['status']})")
                    if step.get('retry_count', 0) > 0:
                        print(f"      Retries: {step['retry_count']}")
            elif expert_mode:
                print(f"\n  ⚠ No execution trace (expected in expert mode)")

            return data.get('session_id')

        else:
            print(f"✗ Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except httpx.ReadTimeout:
        print(f"✗ Request timed out after {TIMEOUT}s")
        print("  This is expected for first run with Ollama (model loading)")
        print("  Try running again - subsequent requests will be faster")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_list_sessions():
    """Test 4: List all sessions."""
    print("\n" + "="*60)
    print("TEST 4: List Sessions")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/v2/chat/sessions")

        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])

            print(f"✓ Sessions retrieved")
            print(f"  - Total sessions: {len(sessions)}")

            if sessions:
                print(f"\n  Recent sessions:")
                for session in sessions[:3]:  # Show first 3
                    print(f"    • {session['title']} (ID: {session['session_id'][:8]}...)")
                    print(f"      Last updated: {session['last_updated']}")

            return True
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_get_history(session_id: str):
    """Test 5: Get session history."""
    print("\n" + "="*60)
    print("TEST 5: Get Session History")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/v2/chat/sessions/{session_id}/history"
            )

        if response.status_code == 200:
            data = response.json()
            history = data.get('history', [])

            print(f"✓ History retrieved")
            print(f"  - Session ID: {data.get('session_id')}")
            print(f"  - Messages: {len(history)}")

            if history:
                print(f"\n  Message history:")
                for i, msg in enumerate(history, 1):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    print(f"    {i}. {role.upper()}: {content[:60]}...")

            return True
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_update_title(session_id: str):
    """Test 6: Update session title."""
    print("\n" + "="*60)
    print("TEST 6: Update Session Title")
    print("="*60)

    try:
        new_title = "Updated API Test Session"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{API_BASE_URL}/api/v2/chat/sessions/{session_id}/title",
                json={"new_title": new_title}
            )

        if response.status_code == 200:
            print(f"✓ Title updated")
            print(f"  - New title: {new_title}")
            return True
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_delete_session(session_id: str):
    """Test 7: Delete session."""
    print("\n" + "="*60)
    print("TEST 7: Delete Session")
    print("="*60)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{API_BASE_URL}/api/v2/chat/sessions/{session_id}"
            )

        if response.status_code == 200:
            print(f"✓ Session deleted")
            print(f"  - Session ID: {session_id}")
            return True
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_expert_mode_message():
    """Test 8: Send message with expert mode enabled."""
    print("\n" + "="*60)
    print("TEST 8: Expert Mode Message")
    print("="*60)

    try:
        request_data = {
            "message": "What is the deepest aquifer?",
            "expert_mode": True
        }

        print(f"Sending request with expert_mode=True")
        print(f"  - Message: {request_data['message']}")
        print()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v2/chat/message",
                json=request_data
            )

        if response.status_code == 200:
            data = response.json()

            execution_trace = data.get('execution_trace')
            if execution_trace and len(execution_trace) > 0:
                print(f"✓ Expert mode working - execution trace present")
                print(f"  - Trace steps: {len(execution_trace)}")

                # Calculate total time
                total_time = sum(step['duration_ms'] for step in execution_trace)
                print(f"  - Total execution time: {total_time:.0f}ms")

                # Show agent breakdown
                print(f"\n  Agent execution breakdown:")
                for step in execution_trace:
                    print(f"    • {step['agent']:20s}: {step['duration_ms']:>6.0f}ms ({step['status']})")

                return True
            else:
                print(f"✗ Expert mode enabled but no execution trace received")
                return False
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except httpx.ReadTimeout:
        print(f"✗ Request timed out")
        print("  Try running again")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def main():
    """Run all API endpoint tests."""
    # Set up logging to file
    from tests.conftest import setup_test_logging, teardown_test_logging
    log_file = setup_test_logging("test_api_endpoints")

    print("\n" + "="*60)
    print("API ENDPOINT TEST SUITE - V2 CHAT")
    print("="*60)
    print(f"\nTesting API at: {API_BASE_URL}")

    results = []
    session_id = None

    # Test 1: Health check
    results.append(await test_health_check())

    # Test 2: Create session
    session_id = await test_create_session()
    results.append(session_id is not None)

    if session_id:
        # Test 3: Send message (normal mode)
        results.append(await test_send_message(session_id, expert_mode=False) is not None)

        # Test 4: List sessions
        results.append(await test_list_sessions())

        # Test 5: Get history
        results.append(await test_get_history(session_id))

        # Test 6: Update title
        results.append(await test_update_title(session_id))

    # Test 7: Expert mode (new session)
    results.append(await test_expert_mode_message())

    # Test 8: Delete session (cleanup)
    if session_id:
        results.append(await test_delete_session(session_id))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All API tests passed!")
        print("\nAPI Integration Complete:")
        print("  ✓ FastAPI endpoints working")
        print("  ✓ LangGraph workflow integrated")
        print("  ✓ Session management functional")
        print("  ✓ Expert mode working")
    else:
        print(f"\n✗ {total - passed} test(s) failed.")

    # Clean up logging
    teardown_test_logging(log_file, passed, total - passed)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
