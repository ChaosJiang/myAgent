"""SQLite-based session manager for conversation persistence."""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any
import aiosqlite

from app.config import settings
from app.models import AgentState


class SessionManager:
    """Manages conversation sessions with SQLite storage."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.database_path
        self._initialized = False

    async def initialize(self):
        """Create database tables if they don't exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    state TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON conversation_history(session_id)
                """
            )
            await db.commit()

        self._initialized = True

    async def get_session(self, session_id: str) -> AgentState | None:
        """
        Retrieve session state by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            AgentState if found, None otherwise
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT state FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    state_dict = json.loads(row[0])
                    return state_dict
                return None

    async def save_session(self, session_id: str, state: AgentState):
        """
        Save or update session state.

        Args:
            session_id: Unique session identifier
            state: Current agent state to persist
        """
        await self.initialize()

        state_json = json.dumps(state)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO sessions (session_id, state, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state = excluded.state,
                    updated_at = excluded.updated_at
                """,
                (session_id, state_json, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Save a conversation message.

        Args:
            session_id: Unique session identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata
        """
        await self.initialize()

        metadata_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversation_history 
                (session_id, role, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, metadata_json, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def get_conversation_history(self, session_id: str) -> list[dict]:
        """
        Get all messages for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of message dictionaries
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT role, content, timestamp, metadata
                FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "metadata": json.loads(row[3]) if row[3] else None,
                    }
                    for row in rows
                ]

    async def delete_expired_sessions(self):
        """Delete sessions older than TTL."""
        await self.initialize()

        ttl_hours = settings.session_ttl_hours
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff.isoformat(),))
            await db.execute(
                """
                DELETE FROM conversation_history 
                WHERE session_id NOT IN (SELECT session_id FROM sessions)
                """
            )
            await db.commit()

    async def create_new_session(self, session_id: str) -> AgentState:
        """
        Create a new session with initial state.

        Args:
            session_id: Unique session identifier

        Returns:
            New AgentState
        """
        initial_state: AgentState = {
            "session_id": session_id,
            "messages": [],
            "parameters": None,
            "missing_params": [],
            "funnel_id": None,
            "funnel_result": None,
            "cohort_result": None,
            "report": None,
            "next_action": "ask_user",
            "error": None,
        }

        await self.save_session(session_id, initial_state)
        return initial_state
