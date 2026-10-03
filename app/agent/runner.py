from langchain_core.messages import HumanMessage, ToolMessage

from app.agent.date_provenance import extract_relative_date
from app.agent.tools import create_reservation_tool
from app.exceptions.reservation import ReservationConflict
from app.llm.client import llm_with_tools,llm
from app.schemas.tool_result import ReservationToolResult
from app.utils.clock import get_current_datetime


def run_agent(user_message: str):

    messages = [
        HumanMessage(content=user_message)
    ]

    # Application-controlled time.
    # The LLM does not determine today's date.
    current_datetime = get_current_datetime("Asia/Kolkata")
    current_date = current_datetime.date()

    # Resolve relative dates from the original user message.
    authoritative_date = extract_relative_date(
        user_message,
        current_date,
    )

    response = llm_with_tools.invoke(messages)

    if not response.tool_calls:
        return response.content

    for tool_call in response.tool_calls:

        tool_name = tool_call["name"]
        args = tool_call["args"]

        print("\nRAW TOOL CALL:")
        print(response.tool_calls)

        if tool_name == "create_reservation_tool":

            # The LLM may incorrectly convert "today"/"tomorrow"
            # into an absolute date.
            #
            # The application-controlled date takes precedence.
            tool_date = args["reservation_date"]

            if authoritative_date is not None:
                tool_date = authoritative_date.isoformat()

            try:

                reservation = create_reservation_tool(
                    party_size=args["party_size"],
                    reservation_date=tool_date,
                    reservation_time=args["reservation_time"],
                    seating=args.get("seating"),
                )

                tool_result = ReservationToolResult(
                    success=True,
                    message="Reservation created successfully.",
                    reservation_id=reservation.id,
                    table_id=reservation.table_id,
                    reservation_date=reservation.date.isoformat(),
                    reservation_time=reservation.start.isoformat(),
                    party_size=reservation.party_size,
                    seating=args.get("seating"),
                )

            except ReservationConflict as exc:

                tool_result = ReservationToolResult(
                    success=False,
                    error_type="availability_conflict",
                    message=str(exc),
                    reservation_date=tool_date,
                    reservation_time=args["reservation_time"],
                    party_size=args["party_size"],
                    seating=args.get("seating"),
                )

            except ValueError as exc:

                tool_result = ReservationToolResult(
                    success=False,
                    error_type="validation_error",
                    message=str(exc),
                    reservation_date=tool_date,
                    reservation_time=args["reservation_time"],
                    party_size=args["party_size"],
                    seating=args.get("seating"),
                )

            messages.append(response)

            messages.append(
                ToolMessage(
                    content=tool_result.model_dump_json(),
                    tool_call_id=tool_call["id"],
                )
            )
    print("\nMESSAGES SENT TO FINAL LLM:")

    for message in messages:
        print("\n---")
        print(message)

    final_response = llm.invoke(messages)

    print("\nFINAL LLM RAW RESPONSE:")
    print(final_response)

    print("\nFINAL LLM CONTENT:")
    print(repr(final_response.content))

    print("\nFINAL LLM TOOL CALLS:")
    print(final_response.tool_calls)

    return final_response.content