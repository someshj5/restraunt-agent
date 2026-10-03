from datetime import date, datetime, time

from app.agent.normalization import (
    normalize_seating,
    resolve_reservation_date,
)
from app.schemas.tool_args import ReservationToolArgs
from app.services.business_rules import validate_reservation_time


def resolve_reservation_time(value: str) -> time:
    value = value.strip()

    formats = [
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported time expression: {value}"
    )


from datetime import date, datetime, time

from app.agent.normalization import (
    normalize_seating,
    resolve_reservation_date,
)
from app.schemas.tool_args import ReservationToolArgs


def resolve_reservation_time(value: str) -> time:
    value = value.strip()

    formats = [
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported time expression: {value}"
    )


def normalize_reservation_tool_args(
    args: dict,
    current_date: date,
):

    normalized = args.copy()

    # Normalize seating BEFORE Pydantic validation.
    if "seating" in normalized:
        normalized["seating"] = normalize_seating(
            normalized["seating"]
        )

    # Normalize date.
    reservation_date_raw = normalized["reservation_date"]

    try:
        normalized["reservation_date"] = date.fromisoformat(
            reservation_date_raw
        )
    except ValueError:
        normalized["reservation_date"] = resolve_reservation_date(
            reservation_date_raw,
            current_date,
        )

    # Normalize time.
    normalized["reservation_time"] = resolve_reservation_time(
        normalized["reservation_time"]
    )



    # Now validate the normalized representation.
    validated = ReservationToolArgs.model_validate(
        normalized
    )

    #Business validation
    validate_reservation_time(
    validated.reservation_date,
    validated.reservation_time,
)

    return (
        validated.reservation_date,
        validated.reservation_time,
        validated.seating,
        validated.party_size,
    )

