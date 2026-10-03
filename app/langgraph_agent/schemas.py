from pydantic import BaseModel


class ReservationExtraction(BaseModel):
    party_size: int | None = None
    reservation_date: str | None = None
    reservation_time: str | None = None
    seating: str | None = None