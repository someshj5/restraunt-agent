from app.agent.tool_adapter import normalize_reservation_tool_args


tests = [
    {
        "name": "valid",
        "args": {
            "party_size": 4,
            "reservation_date": "2026-09-12",
            "reservation_time": "19:00",
            "seating": "outside",
        },
    },
    {
        "name": "too many people",
        "args": {
            "party_size": 50,
            "reservation_date": "2026-09-12",
            "reservation_time": "19:00",
            "seating": "outside",
        },
    },
    {
        "name": "invalid party size",
        "args": {
            "party_size": -2,
            "reservation_date": "2026-09-12",
            "reservation_time": "19:00",
            "seating": "outside",
        },
    },
    {
        "name": "invalid seating",
        "args": {
            "party_size": 4,
            "reservation_date": "2026-09-12",
            "reservation_time": "19:00",
            "seating": "garden",
        },
    },
]


for test in tests:

    print(f"\nTEST: {test['name']}")

    try:
        result = normalize_reservation_tool_args(
            test["args"]
        )

        print("VALID:")
        print(result)

    except Exception as exc:
        print("REJECTED:")
        print(exc)