from datetime import date, timedelta


RELATIVE_DATE_EXPRESSIONS = {
    "today": 0,
    "tomorrow": 1,
}


def extract_relative_date(
    user_message: str,
    current_date: date,
) -> date | None:
    """
    Resolve explicitly stated relative date expressions
    from the original user message.

    Returns None when no supported relative expression
    is present.
    """

    message = user_message.lower()

    for expression, offset in RELATIVE_DATE_EXPRESSIONS.items():
        if expression in message:
            return current_date + timedelta(days=offset)

    return None