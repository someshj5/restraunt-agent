from datetime import date, time, timedelta


INTENT_MAP = {
    "book_table": "reservation",
    "reserve_table": "reservation",
    "make_reservation": "reservation",
    "reservation": "reservation",

    "menu": "menu",
    "order": "order",
}


SEATING_MAP = {
    "outside": "outdoor",
    "outdoors": "outdoor",
    "patio": "outdoor",
    "outdoor": "outdoor",

    "inside": "indoor",
    "indoors": "indoor",
    "indoor": "indoor",
}


def normalize_intent(value: str) -> str:
    return INTENT_MAP.get(
        value.lower().strip(),
        "unknown",
    )


def normalize_seating(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = SEATING_MAP.get(value.lower().strip())

    if normalized is None:
        raise ValueError(
            f"Unsupported seating type: {value}"
        )

    return normalized

from datetime import date, timedelta


from datetime import date, timedelta


def resolve_reservation_date(
    value: str,
    current_date: date,
) -> date:

    normalized = value.strip().lower()

    if normalized == "today":
        return current_date

    if normalized == "tomorrow":
        return current_date + timedelta(days=1)

    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise ValueError(
            f"Unsupported date expression: {value}"
        )

from datetime import datetime, time


def normalize_time(value: str) -> time:

    value = value.strip()

    formats = [
        "%I:%M %p",
        "%I %p",
        "%H:%M",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt,
            ).time()

        except ValueError:
            continue

    raise ValueError(
        f"Unsupported time format: {value}"
    )

def normalize_request(
    data: dict,
    current_date: date,
) -> dict:

    normalized = data.copy()

    normalized["intent"] = normalize_intent(
        data["intent"]
    )

    normalized["seating"] = normalize_seating(
        data.get("seating")
    )

    if data.get("date"):
        normalized["date"] = resolve_relative_date(
            data["date"],
            current_date,
        )

    if data.get("time"):
        normalized["time"] = normalize_time(
            data["time"]
        )

    return normalized