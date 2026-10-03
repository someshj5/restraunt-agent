from datetime import date, time

from app.exceptions.reservation import ReservationConflict
from app.services.reservation_service import ReservationService


service = ReservationService()

reservation = service.create_reservation(
    party_size=4,
    reservation_date=date(2026, 9, 16),
    reservation_time=time(19, 0),
    seating="outdoor",
    idempotency_key="service-test-001",
)

print("Test 1:")
print(reservation)

reservation_retry = service.create_reservation(
    party_size=4,
    reservation_date=date(2026, 9, 16),
    reservation_time=time(19, 0),
    seating="outdoor",
    idempotency_key="service-test-001",
)

print("Test 2:")
print(reservation_retry)

print(
    "Same reservation:",
    reservation.id == reservation_retry.id,
)

print("Test 3:")

try:

    service.create_reservation(
        party_size=6,
        reservation_date=date(2026, 9, 16),
        reservation_time=time(19, 0),
        seating="outdoor",
        idempotency_key="service-test-001",
    )

except ValueError as exc:

    print("Rejected:", exc)

from concurrent.futures import ThreadPoolExecutor


def make_booking(request_number: int):

    try:

        reservation = service.create_reservation(
            party_size=4,
            reservation_date=date(2026, 9, 17),
            reservation_time=time(19, 0),
            seating="outdoor",
            idempotency_key=f"service-concurrent-{request_number}",
        )

        return (
            request_number,
            "success",
            reservation.id,
        )

    except ReservationConflict as exc:

        return (
            request_number,
            "conflict",
            str(exc),
        )


print("Test 4:")

with ThreadPoolExecutor(max_workers=2) as executor:

    results = list(
        executor.map(
            make_booking,
            [1, 2],
        )
    )

for result in results:
    print(result)


def make_idempotent_request(request_number: int):

    try:

        reservation = service.create_reservation(
            party_size=4,
            reservation_date=date(2026, 9, 18),
            reservation_time=time(19, 0),
            seating="outdoor",
            idempotency_key="service-same-key",
        )

        return (
            request_number,
            "success",
            reservation.id,
        )

    except Exception as exc:

        return (
            request_number,
            "error",
            repr(exc),
        )


print("Test 5:")

with ThreadPoolExecutor(max_workers=2) as executor:

    results = list(
        executor.map(
            make_idempotent_request,
            [1, 2],
        )
    )

for result in results:
    print(result)