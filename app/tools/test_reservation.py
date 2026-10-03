from app.schemas.agent import AgentRequest
from app.schemas.reservation import check_availability

if __name__ == "__main__":

    from datetime import date, time

    request = AgentRequest(
        intent="reservation",
        party_size=4,
        date=date(2026, 9, 12),
        time=time(19, 30),
        seating="outdoor",
    )

    result = check_availability(request)

    print(result)