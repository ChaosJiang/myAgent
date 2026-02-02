"""FastAPI application for myAgent."""

from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse, AgentState, ActionType
from app.agent import create_agent_graph
from app.session import SessionManager


session_manager = SessionManager()
agent_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_graph
    await session_manager.initialize()
    agent_graph = create_agent_graph()
    yield


app = FastAPI(
    title="myAgent",
    description="Multi-turn AI agent for funnel analysis with smart routing",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "myAgent",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "session": "/session/{session_id}",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Multi-turn conversation endpoint.

    The agent will:
    1. Route the request intelligently (funnel API, cohort API, or answer from memory)
    2. Validate parameters and ask for missing information
    3. Call appropriate APIs with retry logic
    4. Generate structured reports with insights
    """
    try:
        state = await session_manager.get_session(request.session_id)

        if not state:
            state = await session_manager.create_new_session(request.session_id)

        user_message = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        state["messages"].append(user_message)

        await session_manager.save_message(request.session_id, "user", request.message)

        result = await agent_graph.ainvoke(state)

        await session_manager.save_session(request.session_id, result)

        response_content = ""
        needs_input = False
        missing_params = result.get("missing_params", [])

        if missing_params:
            needs_input = True
            response_content = f"I need more information: {', '.join(missing_params)}"
        elif result.get("error"):
            response_content = f"An error occurred: {result['error']}"
        elif result.get("report"):
            report = result["report"]
            response_content = format_report(report)
        elif result["messages"] and result["messages"][-1]["role"] == "assistant":
            response_content = result["messages"][-1]["content"]
        else:
            response_content = "Request processed successfully."

        if response_content and not (
            result["messages"] and result["messages"][-1]["role"] == "assistant"
        ):
            assistant_message = {
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            result["messages"].append(assistant_message)
            await session_manager.save_session(request.session_id, result)

        await session_manager.save_message(
            request.session_id,
            "assistant",
            response_content,
            metadata={
                "funnel_id": result.get("funnel_id"),
                "action": result.get("next_action"),
            },
        )

        return ChatResponse(
            session_id=request.session_id,
            response=response_content,
            needs_input=needs_input,
            missing_params=missing_params,
            metadata={
                "action_taken": result.get("next_action"),
                "funnel_id": result.get("funnel_id"),
                "has_funnel_result": bool(result.get("funnel_result")),
                "has_cohort_result": bool(result.get("cohort_result")),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    history = await session_manager.get_conversation_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": history}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its history."""
    async with aiosqlite.connect(session_manager.db_path) as db:
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))
        await db.commit()
    return {"status": "deleted", "session_id": session_id}


def format_report(report: dict) -> str:
    """Format structured report as readable text."""
    sections = []

    if "overview" in report:
        sections.append(f"📊 Overview\n{report['overview']}")

    if "metrics" in report and report["metrics"]:
        sections.append(f"\n📈 Key Metrics\n{format_metrics(report['metrics'])}")

    if "insights" in report and report["insights"]:
        insights = "\n".join(f"• {insight}" for insight in report["insights"])
        sections.append(f"\n💡 Insights\n{insights}")

    if "recommendations" in report and report["recommendations"]:
        recs = "\n".join(f"• {rec}" for rec in report["recommendations"])
        sections.append(f"\n🎯 Recommendations\n{recs}")

    return "\n".join(sections)


def format_metrics(metrics: dict) -> str:
    """Format metrics dictionary as readable text."""
    lines = []
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            lines.append(f"• {key}: {value}")
        elif isinstance(value, list):
            lines.append(f"• {key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"• {key}: {value}")
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
