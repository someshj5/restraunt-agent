from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field


class ReservationToolArgs(BaseModel):
    party_size: int = Field(..., ge=1, le=20)
    reservation_date: date
    reservation_time: time
    seating: Literal["indoor", "outdoor"] | None = None