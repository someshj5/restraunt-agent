from datetime import date as Date
from datetime import time as Time
from typing import Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    intent: Literal[
        "reservation",
        "menu",
        "order",
        "unknown"
    ]

    party_size: int | None = Field(
        default=None,
        ge=1,
        le=20
    )

    date: Date | None = None

    time: Time | None = None

    seating: Literal[
        "indoor",
        "outdoor"
    ] | None = None