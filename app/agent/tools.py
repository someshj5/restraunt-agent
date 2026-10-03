from app.agent.tool_adapter import normalize_reservation_tool_args
from app.services.reservation_service import ReservationService
from app.utils.clock import get_current_datetime

reservation_service = ReservationService()


def create_reservation_tool(
    party_size: int,
    reservation_date: str,
    reservation_time: str,
    seating: str | None = None,
):
    """
    Create a restaurant reservation.

    Raw values from the LLM are normalized and validated
    before reaching the reservation service.
    """

    current_datetime = get_current_datetime("Asia/Kolkata")

    (
        normalized_date,
        normalized_time,
        normalized_seating,
        normalized_party_size,
    ) = normalize_reservation_tool_args(
        {
            "party_size": party_size,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "seating": seating,
        },
        current_datetime.date(),
    )

    return reservation_service.create_reservation(
        party_size=normalized_party_size,
        reservation_date=normalized_date,
        reservation_time=normalized_time,
        seating=normalized_seating,
    )