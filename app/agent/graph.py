"""LangGraph state machine definition."""

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    answer_from_context_node,
    call_cohort_api_node,
    call_funnel_api_node,
    generate_report_node,
    route_intent_node,
    validate_parameters_node,
)
from app.models import ActionType, AgentState


def decide_after_route(state: AgentState) -> str:
    """
    Decide next step after routing intent.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    next_action = state.get("next_action", ActionType.ASK_USER.value)

    if next_action == ActionType.CALL_FUNNEL.value:
        return "validate_funnel"
    elif next_action == ActionType.CALL_COHORT.value:
        return "validate_cohort"
    elif next_action == ActionType.ANSWER_CONTEXT.value:
        return "answer_context"
    else:
        return "end"


def decide_after_validate(state: AgentState) -> str:
    """
    Decide next step after parameter validation.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.get("missing_params"):
        return "end"  # Missing params, ask user

    next_action = state.get("next_action")
    if next_action == ActionType.CALL_FUNNEL.value:
        return "call_funnel"
    elif next_action == ActionType.CALL_COHORT.value:
        return "call_cohort"
    else:
        return "end"


def decide_after_api_call(state: AgentState) -> str:
    """
    Decide whether to generate report or end.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.get("error"):
        return "end"  # Error occurred, end flow

    # Generate report if we have results
    if state.get("funnel_result") or state.get("cohort_result"):
        return "generate_report"
    else:
        return "end"


def create_agent_graph():
    """
    Create the LangGraph state machine for the agent.

    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("route_intent", route_intent_node)
    workflow.add_node("validate_funnel", validate_parameters_node)
    workflow.add_node("validate_cohort", validate_parameters_node)
    workflow.add_node("call_funnel", call_funnel_api_node)
    workflow.add_node("call_cohort", call_cohort_api_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("answer_context", answer_from_context_node)

    # Set entry point
    workflow.set_entry_point("route_intent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "route_intent",
        decide_after_route,
        {
            "validate_funnel": "validate_funnel",
            "validate_cohort": "validate_cohort",
            "answer_context": "answer_context",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "validate_funnel",
        decide_after_validate,
        {"call_funnel": "call_funnel", "end": END},
    )

    workflow.add_conditional_edges(
        "validate_cohort",
        decide_after_validate,
        {"call_cohort": "call_cohort", "end": END},
    )

    workflow.add_conditional_edges(
        "call_funnel",
        decide_after_api_call,
        {"generate_report": "generate_report", "end": END},
    )

    workflow.add_conditional_edges(
        "call_cohort",
        decide_after_api_call,
        {"generate_report": "generate_report", "end": END},
    )

    # Direct edges to END
    workflow.add_edge("generate_report", END)
    workflow.add_edge("answer_context", END)

    return workflow.compile()
