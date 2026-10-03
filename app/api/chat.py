from fastapi import APIRouter
from pydantic import BaseModel

from app.llm.client import extract_request

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest):

    structured_request = extract_request(
        request.message
    )

    return {
        "input": request.message,
        "parsed": structured_request.model_dump()
    }

def validate_reservation(request: AgentRequest):

    missing = []

    if request.party_size is None:
        missing.append("party_size")

    if request.date is None:
        missing.append("date")

    if request.time is None:
        missing.append("time")

    return missing