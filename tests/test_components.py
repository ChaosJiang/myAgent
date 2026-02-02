"""Simple test script to verify myAgent components."""

import asyncio
from datetime import datetime

from app.models import FunnelParameters, CohortParameters


async def test_models():
    """Test Pydantic models."""
    print("Testing Pydantic models...")

    funnel_params = FunnelParameters(
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        funnel_steps=["signup", "verify_email", "first_purchase"],
        user_segment="new_users",
    )
    print(f"✓ FunnelParameters: {funnel_params.funnel_steps}")

    cohort_params = CohortParameters(funnel_id="fnl_test123", step_index=1)
    print(f"✓ CohortParameters: {cohort_params.funnel_id}")
    print()


async def test_session_manager():
    """Test session manager."""
    print("Testing SessionManager...")

    from app.session import SessionManager

    manager = SessionManager(db_path="./data/test_sessions.db")
    await manager.initialize()
    print("✓ SessionManager initialized")

    session_id = f"test-{datetime.utcnow().timestamp()}"
    state = await manager.create_new_session(session_id)
    print(f"✓ Created session: {session_id}")

    await manager.save_message(session_id, "user", "Hello")
    await manager.save_message(session_id, "assistant", "Hi there!")

    history = await manager.get_conversation_history(session_id)
    print(f"✓ Saved {len(history)} messages")
    print()


async def test_config():
    """Test configuration."""
    print("Testing configuration...")

    from app.config import settings

    print(f"✓ Funnel API: {settings.funnel_api_base_url}")
    print(f"✓ GCP Project: {settings.gcp_project_id}")
    print(f"✓ Database: {settings.database_path}")
    print()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("myAgent Component Tests")
    print("=" * 60)
    print()

    try:
        await test_config()
        await test_models()
        await test_session_manager()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
