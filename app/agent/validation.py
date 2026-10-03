from app.schemas.agent import AgentRequest

from app.agent.decision import AgentDecision


MAX_PARTY_SIZE = 20
RESTAURANT_OPEN = 11
RESTAURANT_CLOSE = 23


def validate_reservation(
    request: AgentRequest,
) -> AgentDecision:

    missing_fields = []
    errors = []

    if request.party_size is None:
        missing_fields.append("party_size")

    elif request.party_size > MAX_PARTY_SIZE:
        errors.append(
            "Party size exceeds the restaurant's "
            "maximum capacity of 20."
        )

    if request.date is None:
        missing_fields.append("date")

    if request.time is None:
        missing_fields.append("time")

    elif (
        request.time.hour < RESTAURANT_OPEN
        or request.time.hour >= RESTAURANT_CLOSE
    ):
        errors.append(
            "The restaurant is open from "
            "11:00 AM to 11:00 PM."
        )

    if errors:
        return AgentDecision(
            action="reject",
            missing_fields=missing_fields,
            errors=errors,
        )

    if missing_fields:
        return AgentDecision(
            action="ask_user",
            missing_fields=missing_fields,
            errors=[],
        )

    return AgentDecision(
        action="check_availability",
        missing_fields=[],
        errors=[],
    )