"""Example usage script for myAgent with mock API."""

import asyncio
import httpx
from datetime import datetime


MOCK_API_URL = "http://localhost:8080"
AGENT_API_URL = "http://localhost:8000"


async def test_mock_api():
    """Test that the mock API is working."""
    print("=" * 60)
    print("Testing Mock Funnel API")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MOCK_API_URL}/health")
            print(f"✓ Mock API Health: {response.json()['status']}\n")

            funnel_request = {
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-01-31T23:59:59Z",
                "funnel_steps": ["signup", "verify_email", "first_purchase"],
                "user_segment": "new_users",
            }

            response = await client.post(f"{MOCK_API_URL}/api/funnel-analysis", json=funnel_request)
            funnel_data = response.json()
            print(f"✓ Funnel Analysis Response:")
            print(f"  Funnel ID: {funnel_data['funnel_id']}")
            print(f"  Total Users: {funnel_data['total_users']}")
            print(f"  Overall Conversion: {funnel_data['overall_conversion']}%")
            print(f"  Steps: {len(funnel_data['steps'])}\n")

            cohort_request = {
                "funnel_id": funnel_data["funnel_id"],
                "step_index": 1,
            }

            response = await client.post(f"{MOCK_API_URL}/api/cohort-analysis", json=cohort_request)
            cohort_data = response.json()
            print(f"✓ Cohort Analysis Response:")
            print(f"  Step: {cohort_data['step_name']}")
            print(f"  Converted: {cohort_data['converted']['count']}")
            print(f"  Dropped: {cohort_data['dropped']['count']}")
            print(f"  Insights: {len(cohort_data['insights']['key_differences'])}\n")

        except httpx.ConnectError:
            print("❌ Mock API not running!")
            print("Start it with: python mock_api/mock_server.py\n")
            return False

    return True


async def test_agent_with_mock():
    """Test myAgent with the mock API."""

    if not await test_mock_api():
        return

    session_id = f"test-{int(datetime.utcnow().timestamp())}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("Testing myAgent with Mock API")
        print("=" * 60)
        print(f"Session ID: {session_id}\n")

        try:
            response = await client.get(f"{AGENT_API_URL}/health")
            print(f"✓ Agent Health: {response.json()['status']}\n")
        except httpx.ConnectError:
            print("❌ myAgent not running!")
            print("Start it with: python -m app.main\n")
            return

        conversations = [
            "Analyze the signup funnel from January 1 to January 31, 2026. The steps are: signup, verify_email, first_purchase",
            "What's the overall conversion rate?",
            "Why are people dropping off at the verify_email step?",
            "What's the difference between users who convert and those who drop off?",
        ]

        for i, message in enumerate(conversations, 1):
            print("-" * 60)
            print(f"Conversation {i}/{len(conversations)}")
            print("-" * 60)
            print(f"👤 User: {message}")

            response = await client.post(
                f"{AGENT_API_URL}/chat",
                json={"session_id": session_id, "message": message},
            )

            data = response.json()
            print(
                f"🤖 Agent: {data['response'][:300]}{'...' if len(data['response']) > 300 else ''}"
            )
            print(f"📊 Action: {data['metadata']['action_taken']}")

            if data["metadata"].get("funnel_id"):
                print(f"🔑 Funnel ID: {data['metadata']['funnel_id']}")

            print()
            await asyncio.sleep(1)

        print("=" * 60)
        print("Getting Conversation History")
        print("=" * 60)

        response = await client.get(f"{AGENT_API_URL}/session/{session_id}")
        history = response.json()
        print(f"Total messages: {len(history['messages'])}")
        print("\nLast 3 messages:")
        for msg in history["messages"][-3:]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            print(f"{role_emoji} [{msg['role']}] {msg['content'][:100]}...")


async def quick_test():
    """Quick test with minimal output."""
    session_id = f"quick-{int(datetime.utcnow().timestamp())}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Quick Test: Funnel Analysis Request\n")

            response = await client.post(
                f"{AGENT_API_URL}/chat",
                json={
                    "session_id": session_id,
                    "message": "Show me the signup funnel from Jan 1 to Jan 31, 2026. Steps: page_view, signup, purchase",
                },
            )

            data = response.json()
            print(f"Response: {data['response'][:200]}...")
            print(f"\nAction: {data['metadata']['action_taken']}")
            print(f"Funnel ID: {data['metadata'].get('funnel_id', 'N/A')}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import sys

    print("🚀 myAgent Example Usage with Mock API\n")

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(quick_test())
    else:
        print("Prerequisites:")
        print("1. Mock API running on port 8080: python mock_api/mock_server.py")
        print("2. myAgent running on port 8000: python -m app.main")
        print("\nStarting full test...\n")

        try:
            asyncio.run(test_agent_with_mock())
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
