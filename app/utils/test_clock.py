from datetime import date

from app.agent.normalization import resolve_relative_date


CURRENT_DATE = date(2026, 9, 11)


tests = [
    ("today", date(2026, 9, 11)),
    ("tomorrow", date(2026, 9, 12)),
    ("2026-09-15", date(2026, 9, 15)),
]


for expression, expected in tests:

    print(f"\nTEST: {expression}")

    try:
        try:
            result = resolve_relative_date(
                expression,
                CURRENT_DATE,
            )
        except ValueError:
            result = date.fromisoformat(expression)

        print("RESULT:", result)
        print("EXPECTED:", expected)
        print("PASS:", result == expected)

    except Exception as exc:
        print("REJECTED:", exc)