from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.langgraph_agent.nodes import (
    ask_user_node,
    available_node,
    check_availability_node,
    confirmation_node,
    create_reservation_node,
    extract_node,
    llm_extract_node,
    merge_extraction_node,
    normalize_node,
    unavailable_node,
    unclear_confirmation_node,
    validate_node,
)
from app.langgraph_agent.routing import route_after_availability, route_after_confirmation, route_after_validation
from app.langgraph_agent.state import ConversationState


builder = StateGraph(ConversationState)


builder.add_node("extract", llm_extract_node)
builder.add_node("normalize", normalize_node)
builder.add_node("validate", validate_node)
builder.add_node("ask_user", ask_user_node)

builder.add_node("available", available_node)
builder.add_node("unavailable", unavailable_node)

builder.add_node("check_availability", check_availability_node)

builder.add_node("confirmation", confirmation_node)
builder.add_node("create_reservation", create_reservation_node)
builder.add_node("unclear_confirmation",unclear_confirmation_node)
builder.add_node(
    "merge_extraction",
    merge_extraction_node,
)

builder.add_edge(START, "extract")
builder.add_edge("extract","merge_extraction",)
builder.add_edge("merge_extraction","normalize",)
builder.add_edge("normalize", "validate")


builder.add_conditional_edges(
    "validate",
    route_after_validation,
    {
        "ask_user": "ask_user",
        "continue": "check_availability",
    },
)


builder.add_edge("ask_user", "normalize")

builder.add_conditional_edges(
    "check_availability",
    route_after_availability,
    {
        "available": "confirmation",
        "unavailable": "unavailable",
    },
)

builder.add_conditional_edges(
    "confirmation",
    route_after_confirmation,
    {
        "confirm": "create_reservation",
        "cancel": END,
        "unclear": "unclear_confirmation",
    },
)

builder.add_conditional_edges(
    "unclear_confirmation",
    route_after_confirmation,
    {
        "confirm": "create_reservation",
        "cancel": END,
        "unclear": "unclear_confirmation",
    },
)

builder.add_edge("create_reservation", END)

builder.add_edge("available", END)
builder.add_edge("unavailable", END)

from langgraph.checkpoint.postgres import PostgresSaver

# POSTGRES_URI = "postgresql://postgres@localhost:5432/restaurant_agent"
POSTGRES_URI = "postgresql://someshjaiswal@localhost:5432/restaurant_agent"


checkpointer_context = PostgresSaver.from_conn_string(POSTGRES_URI)
checkpointer = checkpointer_context.__enter__()

checkpointer.setup()

graph = builder.compile(checkpointer=checkpointer)

# graph = builder.compile(checkpointer=checkpointer)
def get_pending_interrupt(config):
    state = graph.get_state(config)

    if not state.tasks:
        return None

    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0]

    return None

if __name__ == "__main__":
    config = {
    "configurable": {
        "thread_id": "postgres_test_001"
    }
}
    print("\n===== RESTAURANT AGENT =====")
    print("Type 'quit' to exit.\n")

    while True:
        user_message = input("You: ")

        if user_message.lower() == "quit":
            break

        pending_interrupt = get_pending_interrupt(config)

        if pending_interrupt:
            result = graph.invoke(
                Command(resume=user_message),
                config=config,
            )
        else:
            result = graph.invoke(
                {"user_message": user_message},
                config=config,
            )

        while "__interrupt__" in result:
            interrupt = result["__interrupt__"][0]

            print(f"Agent: {interrupt.value}")

            user_answer = input("You: ")

            if user_answer.lower() == "quit":
                break

            result = graph.invoke(
                Command(resume=user_answer),
                config=config,
            )

        if result.get("response"):
            print(f"Agent: {result['response']}")