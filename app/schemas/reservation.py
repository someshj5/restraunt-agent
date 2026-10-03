from datetime import date, datetime, time

from pydantic import BaseModel


class Reservation(BaseModel):
    id: str
    table_id: str
    party_size: int
    date: date
    start: time
    end: time