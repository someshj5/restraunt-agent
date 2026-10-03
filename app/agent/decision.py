from typing import Literal

from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    action: Literal[
        "ask_user",
        "reject",
        "check_availability",
        "search_menu",
        "create_order",
        "unknown",
    ]

    missing_fields: list[str] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)