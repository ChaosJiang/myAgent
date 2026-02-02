"""Agent node implementations for LangGraph."""

from datetime import datetime

from app.llm import VertexAIRouter
from app.models import ActionType, AgentState, CohortParameters, FunnelParameters
from app.tools import CohortAPIClient, FunnelAPIClient


async def route_intent_node(state: AgentState) -> AgentState:
    """
    Use LLM to decide next action: call funnel API, cohort API, or answer from context.

    Args:
        state: Current agent state

    Returns:
        Updated state with next_action set
    """
    router = VertexAIRouter()

    user_message = state["messages"][-1]["content"]

    try:
        action_name, parameters = await router.route_request(
            user_message=user_message,
            funnel_id=state.get("funnel_id"),
            funnel_result=state.get("funnel_result"),
            cohort_result=state.get("cohort_result"),
        )

        # Map function names to action types
        action_map = {
            "analyze_funnel": ActionType.CALL_FUNNEL,
            "analyze_cohort": ActionType.CALL_COHORT,
            "answer_from_memory": ActionType.ANSWER_CONTEXT,
        }

        next_action = action_map.get(action_name, ActionType.ANSWER_CONTEXT)

        # Update state
        new_state = state.copy()
        new_state["next_action"] = next_action.value
        new_state["parameters"] = parameters

        return new_state

    except Exception as e:
        # On error, try to answer from context or ask user
        new_state = state.copy()
        new_state["next_action"] = ActionType.ASK_USER.value
        new_state["error"] = str(e)
        new_state["missing_params"] = ["Unable to process request"]
        return new_state


async def validate_parameters_node(state: AgentState) -> AgentState:
    """
    Validate that required parameters are present based on next_action.

    Args:
        state: Current agent state

    Returns:
        Updated state with missing_params populated if validation fails
    """
    new_state = state.copy()
    params = state.get("parameters", {})
    missing = []

    next_action = state.get("next_action")

    if next_action == ActionType.CALL_FUNNEL.value:
        # Validate funnel parameters
        required = ["start_date", "end_date", "funnel_steps"]
        missing = [p for p in required if not params.get(p)]

        # Validate funnel_steps has at least 2 items
        if "funnel_steps" not in missing:
            steps = params.get("funnel_steps", [])
            if not isinstance(steps, list) or len(steps) < 2:
                missing.append("funnel_steps (need at least 2 steps)")

    elif next_action == ActionType.CALL_COHORT.value:
        # Validate cohort parameters
        if not state.get("funnel_id"):
            missing.append("funnel_id (run funnel analysis first)")
        if "step_index" not in params:
            missing.append("step_index")

    new_state["missing_params"] = missing
    return new_state


async def call_funnel_api_node(state: AgentState) -> AgentState:
    """
    Call the funnel analysis API.

    Args:
        state: Current agent state

    Returns:
        Updated state with funnel_result and funnel_id
    """
    client = FunnelAPIClient()
    params = state["parameters"]

    try:
        # Convert string dates to datetime if needed
        start_date = params["start_date"]
        end_date = params["end_date"]

        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        funnel_params = FunnelParameters(
            start_date=start_date,
            end_date=end_date,
            funnel_steps=params["funnel_steps"],
            user_segment=params.get("user_segment"),
        )

        result = await client.analyze_funnel(funnel_params)

        # Update state
        new_state = state.copy()
        new_state["funnel_id"] = result.funnel_id
        new_state["funnel_result"] = result.model_dump()
        new_state["next_action"] = ActionType.END.value

        return new_state

    except Exception as e:
        new_state = state.copy()
        new_state["error"] = f"Funnel API error: {str(e)}"
        new_state["next_action"] = ActionType.ASK_USER.value
        return new_state


async def call_cohort_api_node(state: AgentState) -> AgentState:
    """
    Call the cohort analysis API.

    Args:
        state: Current agent state

    Returns:
        Updated state with cohort_result
    """
    client = CohortAPIClient()
    params = state["parameters"]

    try:
        cohort_params = CohortParameters(
            funnel_id=state["funnel_id"], step_index=params["step_index"]
        )

        result = await client.analyze_cohort(cohort_params)

        # Update state
        new_state = state.copy()
        new_state["cohort_result"] = result.model_dump()
        new_state["next_action"] = ActionType.END.value

        return new_state

    except Exception as e:
        new_state = state.copy()
        new_state["error"] = f"Cohort API error: {str(e)}"
        new_state["next_action"] = ActionType.ASK_USER.value
        return new_state


async def generate_report_node(state: AgentState) -> AgentState:
    """
    Generate structured report from analysis results.

    Args:
        state: Current agent state

    Returns:
        Updated state with report
    """
    router = VertexAIRouter()

    try:
        report = await router.generate_report(
            funnel_result=state.get("funnel_result"), cohort_result=state.get("cohort_result")
        )

        new_state = state.copy()
        new_state["report"] = report
        return new_state

    except Exception as e:
        # Fallback to basic report
        new_state = state.copy()
        new_state["report"] = {
            "overview": "Analysis completed",
            "metrics": state.get("funnel_result", {}) or state.get("cohort_result", {}),
            "insights": [f"Error generating insights: {str(e)}"],
            "recommendations": ["Review raw data for details"],
        }
        return new_state


async def answer_from_context_node(state: AgentState) -> AgentState:
    """
    Answer user's question using existing context (no API call).

    Args:
        state: Current agent state with answer in parameters

    Returns:
        Updated state with assistant message
    """
    params = state.get("parameters", {})
    answer = params.get("answer", "I don't have enough information to answer that question.")

    # Add assistant message
    new_state = state.copy()
    new_state["messages"] = state["messages"] + [
        {"role": "assistant", "content": answer, "timestamp": datetime.utcnow().isoformat()}
    ]
    new_state["next_action"] = ActionType.END.value

    return new_state
