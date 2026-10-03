import os
from datetime import date, datetime, time, timedelta

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from app.exceptions.reservation import ReservationConflict
from app.langgraph_agent.schemas import ReservationExtraction
from app.langgraph_agent.state import ConversationState
from app.services.reservation_service import ReservationService


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI(
    model="meta/muse-glimmer-30b",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NV_API_KEY"),
    temperature=0,
)

# Kept because it may be useful later when we revisit
# structured output. Currently extraction uses native tool calling.
structured_llm = llm.with_structured_output(
    ReservationExtraction
)


# ============================================================
# RESERVATION EXTRACTION TOOL
# ============================================================

@tool
def extract_reservation_details(
    party_size: int | None = None,
    reservation_date: str | None = None,
    reservation_time: str | None = None,
    seating: str | None = None,
):
    """
    Extract reservation details from the user's message.

    Do not invent missing information.
    Return None for fields that are not explicitly available.
    """
    return {
        "party_size": party_size,
        "reservation_date": reservation_date,
        "reservation_time": reservation_time,
        "seating": seating,
    }


llm_with_extraction_tool = llm.bind_tools(
    [extract_reservation_details]
)


# ============================================================
# LLM EXTRACTION NODE
# ============================================================

def llm_extract_node(state: ConversationState):
    print("\n--- LLM EXTRACT NODE ---")

    user_message = state["user_message"]

    messages = [
        (
            "system",
            """
            You extract reservation information from the user's message.

            Extract only information that is actually present.

            Fields:
            - party_size
            - reservation_date
            - reservation_time
            - seating

            For reservation_date:
            - If the user gives an absolute date, return it as YYYY-MM-DD.
            - If the user gives a relative date such as "today", "tomorrow",
              or "next Friday", return the original relative expression exactly.
            - Do not calculate or invent the actual calendar date.

            For reservation_time:
            - Return the time as the user expressed it, such as "8 PM"
              or "8:30 PM".
            - Do not invent a time.

            If a field is missing, return None.

            Do not invent values.
            Do not make assumptions.
            Use the extraction tool.
            """,
        ),
        ("human", user_message),
    ]

    response = llm_with_extraction_tool.invoke(messages)

    print("LLM response:", response)

    if not response.tool_calls:
        raise ValueError("LLM did not call extraction tool")

    tool_call = response.tool_calls[0]

    print("Extracted arguments:", tool_call["args"])

    args = tool_call["args"]

    def clean(value):
        if value is None:
            return None

        if isinstance(value, str) and value.strip().lower() in {
            "",
            "none",
            "null",
        }:
            return None

        return value

    return {
        "extracted_party_size": args.get("party_size"),
        "extracted_date": clean(args.get("reservation_date")),
        "extracted_time": clean(args.get("reservation_time")),
        "extracted_seating": clean(args.get("seating")),
    }


# ============================================================
# MERGE EXTRACTION NODE
# ============================================================

def merge_extraction_node(state: ConversationState):
    print("\n--- MERGE EXTRACTION NODE ---")

    updates = {}

    extracted_party_size = state.get("extracted_party_size")
    extracted_date = state.get("extracted_date")
    extracted_time = state.get("extracted_time")
    extracted_seating = state.get("extracted_seating")

    # New non-null values overwrite existing state.
    # Missing values preserve existing state.

    if extracted_party_size is not None:
        updates["party_size"] = extracted_party_size

    if extracted_date is not None:
        updates["date"] = extracted_date

    if extracted_time is not None:
        updates["time"] = extracted_time

    if extracted_seating is not None:
        updates["seating"] = extracted_seating

    # Extraction fields are temporary processing state.
    updates["extracted_party_size"] = None
    updates["extracted_date"] = None
    updates["extracted_time"] = None
    updates["extracted_seating"] = None

    print("MERGE UPDATES:", updates)

    return updates


# ============================================================
# LEGACY / TEST EXTRACTION NODE
# ============================================================
# Kept because graph.py currently imports this node.
# The production graph uses llm_extract_node instead.

def extract_node(state: ConversationState):
    print("\n--- EXTRACT NODE ---")

    user_message = state["user_message"].lower()

    updates = {}

    if state.get("party_size") is None:
        if "4" in user_message:
            updates["party_size"] = 4

    if state.get("date") is None:
        if "tomorrow" in user_message:
            updates["date"] = "2026-09-14"

    if state.get("time") is None:
        if "8 pm" in user_message:
            updates["time"] = "20:00"

    if state.get("time") is None:
        if "10 pm" in user_message:
            updates["time"] = "22:00"

    return updates


# ============================================================
# TIME NORMALIZATION HELPER
# ============================================================

def parse_time(value: str) -> time:
    """
    Convert common human-readable time representations
    into canonical datetime.time.
    """

    value = value.strip()

    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue

    raise ValueError(f"Invalid time format: {value}")


# ============================================================
# NORMALIZE NODE
# ============================================================

def normalize_node(state: ConversationState):
    print("\n--- NORMALIZE NODE ---")
    print("STATE ENTERING NORMALIZE:", state)

    updates = {}

    # --------------------------------------------------------
    # 1. Normalize DATE
    # --------------------------------------------------------

    raw_date = state.get("date")

    if isinstance(raw_date, date):
        updates["date"] = raw_date

    elif isinstance(raw_date, str):
        raw_date = raw_date.strip()

        if raw_date.lower() in {"", "none", "null"}:
            updates["date"] = None

        elif raw_date.lower() == "tomorrow":
            updates["date"] = date.today() + timedelta(days=1)

        elif raw_date.lower() == "today":
            updates["date"] = date.today()

        else:
            updates["date"] = datetime.strptime(
                raw_date,
                "%Y-%m-%d",
            ).date()

    # --------------------------------------------------------
    # 2. Normalize TIME already in canonical state
    # --------------------------------------------------------

    raw_time = state.get("time")

    if isinstance(raw_time, time):
        updates["time"] = raw_time

    elif isinstance(raw_time, str):
        raw_time = raw_time.strip()

        if raw_time.lower() in {"", "none", "null"}:
            updates["time"] = None

        else:
            updates["time"] = parse_time(raw_time)

    # --------------------------------------------------------
    # 3. Normalize newly supplied interrupt input
    # --------------------------------------------------------

    pending_input = state.get("pending_input")

    if pending_input:
        raw_input = pending_input.strip()

        if raw_input.lower() in {"", "none", "null"}:
            updates["pending_input"] = None

        else:
            updates["time"] = parse_time(raw_input)
            updates["pending_input"] = None

    print("NORMALIZE UPDATES:", updates)

    return updates


# ============================================================
# VALIDATION NODE
# ============================================================

def validate_node(state: ConversationState):
    print("\n--- VALIDATE NODE ---")

    missing_fields = []

    if state.get("party_size") is None:
        missing_fields.append("party_size")

    if state.get("date") is None:
        missing_fields.append("date")

    if state.get("time") is None:
        missing_fields.append("time")

    print("Missing fields:", missing_fields)

    if missing_fields:
        return {
            "missing_fields": missing_fields,
            "workflow_status": "COLLECTING_DETAILS",
        }

    return {
        "missing_fields": [],
        "workflow_status": "CHECKING_AVAILABILITY",
    }


# ============================================================
# AVAILABILITY NODE
# ============================================================

def check_availability_node(state: ConversationState):
    print("\n--- AVAILABILITY NODE ---")

    service = ReservationService()

    available = service.check_availability(
        party_size=state["party_size"],
        reservation_date=state["date"],
        reservation_time=state["time"],
        seating=state.get("seating"),
    )

    if available:
        message = (
            f"A table is available for "
            f"{state['party_size']} people at "
            f"{state['time'].strftime('%H:%M')}."
        )

        return {
            "available": True,
            "availability_message": message,
            "response": message,
            "workflow_status": "AWAITING_CONFIRMATION",
        }

    message = "Sorry, no table is available for that time."

    return {
        "available": False,
        "availability_message": message,
        "response": message,
        "workflow_status": "UNAVAILABLE",
    }


# ============================================================
# AVAILABLE NODE
# ============================================================

def available_node(state: ConversationState):
    print("\n--- AVAILABLE NODE ---")

    return {
        "response": state["availability_message"],
    }


# ============================================================
# UNAVAILABLE NODE
# ============================================================

def unavailable_node(state: ConversationState):
    print("\n--- UNAVAILABLE NODE ---")

    return {
        "response": state["availability_message"],
        "workflow_status": "UNAVAILABLE",
    }


# ============================================================
# CONFIRMATION NODE
# ============================================================

def confirmation_node(state: ConversationState):
    print("\n--- CONFIRMATION NODE ---")

    answer = interrupt(
        "A table is available. Would you like me to book it?"
    )

    return {
        "confirmation": answer,
        "confirmation_status": "RECEIVED",
        "workflow_status": "AWAITING_CONFIRMATION",
    }


# ============================================================
# UNCLEAR CONFIRMATION NODE
# ============================================================

def unclear_confirmation_node(state: ConversationState):
    print("\n--- UNCLEAR CONFIRMATION NODE ---")

    answer = interrupt(
        "I didn't quite understand. "
        "Would you like me to book the table? "
        "Please answer yes or no."
    )

    return {
        "confirmation": answer,
        "confirmation_status": "RECEIVED",
        "workflow_status": "AWAITING_CONFIRMATION",
    }


# ============================================================
# CREATE RESERVATION NODE
# ============================================================

def create_reservation_node(state: ConversationState):
    print("\n--- CREATE RESERVATION NODE ---")

    service = ReservationService()

    try:
        reservation = service.create_reservation(
            party_size=state["party_size"],
            reservation_date=state["date"],
            reservation_time=state["time"],
            seating=state.get("seating"),
        )

        response = (
            f"Your table is booked successfully. "
            f"Reservation ID: {reservation.id}"
        )

        return {
            "response": response,
            "workflow_status": "BOOKED",
        }

    except ReservationConflict:
        return {
            "response": (
                "Sorry, the table was just taken by another "
                "reservation. Please choose another time."
            ),
            "workflow_status": "BOOKING_CONFLICT",
        }


# ============================================================
# ASK USER NODE
# ============================================================

def ask_user_node(state: ConversationState):
    print("\n--- ASK USER NODE ---")

    answer = interrupt(
        "What time would you like?"
    )

    return {
        "pending_input": answer,
        "response": None,
        "workflow_status": "COLLECTING_DETAILS",
    }