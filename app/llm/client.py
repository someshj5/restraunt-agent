import os
from app.schemas.agent import AgentRequest
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
# from langchain_core.documents import Document
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS


from langchain_openai import ChatOpenAI

from app.schemas.agent import AgentRequest
from app.llm.prompts import SYSTEM_PROMPT
from app.agent.tools import create_reservation_tool

llm = ChatOpenAI(
    model="meta/muse-glimmer-30b",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NV_API_KEY"),
    temperature=0.95,
)

llm_with_tools = llm.bind_tools(
    [create_reservation_tool]
)

# structured_llm = llm.with_structured_output(
#     AgentRequest
# )


# def extract_request(user_message: str) -> AgentRequest:
#     """
#     Convert natural language into a validated AgentRequest.
#     """

#     response = structured_llm.invoke(
#         user_message
#     )

#     return response


from langchain_core.messages import HumanMessage, SystemMessage
import json
from app.agent.normalization import normalize_request, normalize_seating
from datetime import date 
from datetime import time 

def extract_request(user_message: str) -> AgentRequest:

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    data = json.loads(response.content)
    print('__56__',data)
    normalized = normalize_request(
    data,
    current_date=date.today(),
)


    request = AgentRequest.model_validate(normalized)

    return request

if __name__ == "__main__":

    response = llm_with_tools.invoke(
    "Book a table for 4 people tomorrow at 7 PM outside."
    )

    print(response)
    print(response.tool_calls)

    tool_call = response.tool_calls[0]

    print(tool_call["name"])
    print(tool_call["args"])

    args = tool_call["args"]

    reservation = create_reservation_tool(
        party_size=args["party_size"],
        reservation_date=date.fromisoformat(
            args["reservation_date"]
        ),
        reservation_time=time.fromisoformat(
            args["reservation_time"]
        ),
        seating=normalize_seating(args["seating"]),
        idempotency_key=tool_call["id"],
    )

    print(reservation)

    # user_q = "Book a table for 4 people tomorrow at 7:30 PM, preferably outside."
    # resp = extract_request(user_q)
    # print(resp)


