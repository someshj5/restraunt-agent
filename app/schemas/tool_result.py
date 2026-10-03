from pydantic import BaseModel


class ReservationToolResult(BaseModel):
    success: bool
    error_type: str | None = None
    message: str

    reservation_id: str | None = None
    table_id: str | None = None

    reservation_date: str
    reservation_time: str
    party_size: int
    seating: str | None = None