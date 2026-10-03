from app.langgraph_agent.state import ConversationState


def route_after_validation(state: ConversationState):
    if state.get("missing_fields"):
        return "ask_user"

    return "continue"


def route_after_availability(state: ConversationState):
    if state.get("available"):
        return "available"

    return "unavailable"

def route_after_confirmation(state: ConversationState):
    answer = state.get("confirmation")

    if answer is None:
        return "unclear"

    answer = answer.strip().lower()

    yes_values = {
        "yes",
        "y",
        "yeah",
        "yep",
        "sure",
        "okay",
        "ok",
        "confirm",
        "book it",
    }

    no_values = {
        "no",
        "n",
        "nope",
        "cancel",
        "don't book",
        "do not book",
    }

    if answer in yes_values:
        return "confirm"

    if answer in no_values:
        return "cancel"

    return "unclear"