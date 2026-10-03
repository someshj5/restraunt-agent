from datetime import date, datetime, time, timedelta


OPENING_TIME = time(11, 0)
CLOSING_TIME = time(23, 0)
RESERVATION_DURATION = timedelta(minutes=90)


def validate_reservation_time(
    reservation_date: date,
    reservation_time: time,
):
    reservation_start = datetime.combine(
        reservation_date,
        reservation_time,
    )

    opening = datetime.combine(
        reservation_date,
        OPENING_TIME,
    )

    closing = datetime.combine(
        reservation_date,
        CLOSING_TIME,
    )

    reservation_end = (
        reservation_start + RESERVATION_DURATION
    )

    if reservation_start < opening:
        raise ValueError(
            "Reservations cannot start before 11:00."
        )

    if reservation_end > closing:
        raise ValueError(
            "The reservation would extend beyond "
            "the restaurant's closing time of 23:00."
        )