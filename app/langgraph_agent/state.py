from datetime import date, time
from typing import TypedDict


class ConversationState(TypedDict, total=False):
    user_message: str

    # Reservation data
    party_size: int | None
    date: date | None
    time: time | None
    seating: str | None

    # Raw LLM extraction
    extracted_party_size: int | None
    extracted_date: str | None
    extracted_time: str | None
    extracted_seating: str | None

    # Validation
    missing_fields: list[str]

    # Workflow state
    workflow_status: str | None

    # Interrupt / conversation
    pending_input: str | None

    # Availability
    available: bool | None
    availability_message: str | None

    # Confirmation
    confirmation: str | None
    confirmation_status: str | None

    # User-facing response
    response: str | None

