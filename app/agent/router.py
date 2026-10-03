from app.agent.validation import validate_reservation
from app.schemas.agent import AgentRequest


def decide_next_action(
    request: AgentRequest,
) -> str:

    if request.intent == "reservation":

        errors = validate_reservation(request)

        if errors:
            return "ask_user"

        return "check_availability"

    if request.intent == "menu":
        return "search_menu"

    if request.intent == "order":
        return "create_order"

    return "unknown"