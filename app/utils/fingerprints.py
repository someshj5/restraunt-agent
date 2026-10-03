
import hashlib
import json
from datetime import date, datetime, time, timedelta


def build_request_fingerprint(
    party_size: int,
    reservation_date: date,
    reservation_time: time,
    seating: str | None,
) -> str:
    payload = {
        "party_size": party_size,
        "date": reservation_date.isoformat(),
        "time": reservation_time.isoformat(),
        "seating": seating,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

