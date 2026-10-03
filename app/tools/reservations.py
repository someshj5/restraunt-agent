from datetime import date, datetime, time, timedelta
from app.schemas.reservation import Reservation
from pydantic import BaseModel
import time as time_module

RESERVATION_DURATION = timedelta(minutes=90)


TABLES = [
    {"id": "T1", "capacity": 2, "seating": "indoor"},
    {"id": "T2", "capacity": 4, "seating": "outdoor"},
    {"id": "T3", "capacity": 4, "seating": "indoor"},
    {"id": "T4", "capacity": 6, "seating": "outdoor"},
    {"id": "T5", "capacity": 8, "seating": "indoor"},
]


RESERVATIONS = [
    {
        "id": "R1",
        "table_id": "T2",
        "date": date(2026, 9, 12),
        "start": time(19, 0),
        "end": time(20, 0),
    }
]


class AvailabilityResult(BaseModel):
    available: bool
    table_ids: list[str]
    message: str


from app.db.connection import get_connection

from datetime import date, datetime, time, timedelta
from uuid import uuid4

import psycopg
from pydantic import BaseModel

from app.db.connection import get_connection
from app.exceptions.reservation import ReservationConflict
from app.schemas.reservation import Reservation


RESERVATION_DURATION = timedelta(minutes=90)


def create_reservation(
    party_size: int,
    reservation_date: date,
    reservation_time: time,
    seating: str | None = None,
    idempotency_key: str | None = None,
) -> Reservation:

    fingerprint = build_request_fingerprint(
        party_size=party_size,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        seating=seating,
    )

    requested_start = datetime.combine(
        reservation_date,
        reservation_time,
    )

    requested_end = requested_start + RESERVATION_DURATION

    with get_connection() as conn:

        # =========================================================
        # 1. Fast path: check whether this request already exists
        # =========================================================

        if idempotency_key is not None:

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        table_id,
                        party_size,
                        start_at,
                        end_at,
                        request_fingerprint
                    FROM reservations
                    WHERE idempotency_key = %s
                    """,
                    (idempotency_key,),
                )

                existing = cursor.fetchone()

            if existing:

                if existing[5] != fingerprint:
                    raise ValueError(
                        "Idempotency key was already used "
                        "for a different reservation request."
                    )

                return Reservation(
                    id=str(existing[0]),
                    table_id=str(existing[1]),
                    party_size=existing[2],
                    date=existing[3].date(),
                    start=existing[3].time(),
                    end=existing[4].time(),
                )

        try:

            # =====================================================
            # 2. Find an available table
            # =====================================================

            query = """
                SELECT t.id
                FROM restaurant_tables t
                WHERE t.capacity >= %s
            """

            params = [party_size]

            if seating is not None:
                query += """
                    AND t.seating = %s
                """
                params.append(seating)

            query += """
                AND NOT EXISTS (
                    SELECT 1
                    FROM reservations r
                    WHERE r.table_id = t.id
                      AND r.status IN ('pending', 'confirmed')
                      AND tstzrange(
                          r.start_at,
                          r.end_at,
                          '[)'
                      )
                      &&
                      tstzrange(
                          %s,
                          %s,
                          '[)'
                      )
                )
                ORDER BY t.capacity ASC
                LIMIT 1
            """

            params.extend([
                requested_start,
                requested_end,
            ])

            with conn.cursor() as cursor:

                cursor.execute(query, params)

                row = cursor.fetchone()

                if row is None:
                    raise ReservationConflict(
                        "No table is available for the requested time."
                    )

                table_id = row[0]

                # =================================================
                # 3. Attempt INSERT
                # =================================================

                reservation_id = uuid4()

                try:

                    cursor.execute(
                        """
                        INSERT INTO reservations (
                            id,
                            table_id,
                            party_size,
                            start_at,
                            end_at,
                            status,
                            idempotency_key,
                            request_fingerprint
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        RETURNING
                            id,
                            table_id,
                            party_size,
                            start_at,
                            end_at
                        """,
                        (
                            reservation_id,
                            table_id,
                            party_size,
                            requested_start,
                            requested_end,
                            "confirmed",
                            idempotency_key,
                            fingerprint,
                        ),
                    )

                    result = cursor.fetchone()

                    return Reservation(
                        id=str(result[0]),
                        table_id=str(result[1]),
                        party_size=result[2],
                        date=result[3].date(),
                        start=result[3].time(),
                        end=result[4].time(),
                    )

                # ================================================
                # 4. Same idempotency key raced with us
                # ================================================

                except psycopg.errors.UniqueViolation as exc:

                    # Roll back the failed INSERT transaction so
                    # the connection can be used again.
                    conn.rollback()

                    if idempotency_key is None:
                        raise

                    with conn.cursor() as retry_cursor:

                        retry_cursor.execute(
                            """
                            SELECT
                                id,
                                table_id,
                                party_size,
                                start_at,
                                end_at,
                                request_fingerprint
                            FROM reservations
                            WHERE idempotency_key = %s
                            """,
                            (idempotency_key,),
                        )

                        existing = retry_cursor.fetchone()

                    if existing is None:
                        # The UniqueViolation was not caused by the
                        # idempotency key we expected.
                        raise exc

                    if existing[5] != fingerprint:
                        raise ValueError(
                            "Idempotency key was already used "
                            "for a different reservation request."
                        )

                    return Reservation(
                        id=str(existing[0]),
                        table_id=str(existing[1]),
                        party_size=existing[2],
                        date=existing[3].date(),
                        start=existing[3].time(),
                        end=existing[4].time(),
                    )

        except psycopg.errors.ExclusionViolation as exc:

            raise ReservationConflict(
                "The selected table is no longer available."
            ) from exc

def check_availability(
    party_size: int,
    reservation_date: date,
    reservation_time: time,
    seating: str | None = None,
) -> AvailabilityResult:

    requested_start = datetime.combine(
        reservation_date,
        reservation_time,
    )

    requested_end = requested_start + RESERVATION_DURATION

    query = """
    SELECT t.id
    FROM restaurant_tables t
    WHERE t.capacity >= %s
"""

    params = [party_size]

    if seating is not None:
        query += """
            AND t.seating = %s
        """
        params.append(seating)

    query += """
    AND NOT EXISTS (
        SELECT 1
        FROM reservations r
        WHERE r.table_id = t.id
          AND r.status IN ('pending', 'confirmed')
          AND tstzrange(r.start_at, r.end_at, '[)')
              && tstzrange(%s, %s, '[)')
    )
    ORDER BY t.capacity ASC
"""

    params.extend([
        requested_start,
        requested_end,
    ])

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                query,
                params
            )

            rows = cursor.fetchall()

    table_ids = [str(row[0]) for row in rows]

    if table_ids:
        return AvailabilityResult(
            available=True,
            table_ids=table_ids,
            message=f"Available tables: {', '.join(table_ids)}",
        )

    return AvailabilityResult(
        available=False,
        table_ids=[],
        message="No suitable tables are available for the requested time.",
    )


def create_reservation_unsafe(
    reservation_id: str,
    party_size: int,
    reservation_date: date,
    reservation_time: time,
    seating: str | None = None,
) -> Reservation:

    availability = check_availability(
        party_size=party_size,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        seating=seating,
    )

    if not availability.available:
        raise ValueError("No table available")

    # Simulate some processing/network/database delay.
    time_module.sleep(0.5)

    table_id = availability.table_ids[0]

    requested_start = datetime.combine(
        reservation_date,
        reservation_time,
    )

    requested_end = requested_start + RESERVATION_DURATION

    reservation = Reservation(
        id=reservation_id,
        table_id=table_id,
        party_size=party_size,
        date=reservation_date,
        start=requested_start.time(),
        end=requested_end.time(),
    )

    RESERVATIONS.append(reservation.model_dump())

    return reservation


import hashlib
import json


def build_request_fingerprint(
    party_size: int,
    reservation_date: date,
    reservation_time: time,
    seating: str | None,
) -> str:
    payload = {
        "party_size": party_size,
        "date": reservation_date.isoformat(),
        "time": reservation_time.isoformat(),
        "seating": seating,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


from concurrent.futures import ThreadPoolExecutor

def concurrent_booking_test():
    def make_booking(request_number: int):
        try:
            reservation = create_reservation(
                party_size=4,
                reservation_date=date(2026, 9, 14),
                reservation_time=time(19, 0),
                seating="outdoor",
                idempotency_key=f"concurrent-test-{request_number}",
            )

            return {
                "request": request_number,
                "status": "success",
                "reservation_id": reservation.id,
                "table_id": reservation.table_id,
            }

        except ReservationConflict as exc:
            return {
                "request": request_number,
                "status": "conflict",
                "error": str(exc),
            }

        except Exception as exc:
            return {
                "request": request_number,
                "status": "error",
                "error": repr(exc),
            }

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                make_booking,
                [1, 2],
            )
        )

    for result in results:
        print(result)

def concurrent_idempotency_test():

    def make_request(request_number: int):

        try:
            reservation = create_reservation(
                party_size=4,
                reservation_date=date(2026, 9, 15),
                reservation_time=time(19, 0),
                seating="outdoor",
                idempotency_key="same-concurrent-key",
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

    with ThreadPoolExecutor(max_workers=2) as executor:

        results = list(
            executor.map(
                make_request,
                [1, 2],
            )
        )

    for result in results:
        print(result)

if __name__ == "__main__":

    concurrent_idempotency_test()

    key = "demo-idempotency-001"

    # reservation_1 = create_reservation(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 13),
    #     reservation_time=time(19, 0),
    #     seating="outdoor",
    #     idempotency_key=key,
    # )

    # reservation_2 = create_reservation(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 13),
    #     reservation_time=time(19, 0),
    #     seating="outdoor",
    #     idempotency_key=key,
    # )

    # print("First:", reservation_1)
    # print("Second:", reservation_2)
    # print("Same reservation:", reservation_1.id == reservation_2.id)
    # try:
    #     reservation_3 = create_reservation(
    #         party_size=6,
    #         reservation_date=date(2026, 9, 13),
    #         reservation_time=time(19, 0),
    #         seating="outdoor",
    #         idempotency_key=key,
    #     )

    #     print(reservation_3)

    # except ValueError as exc:
    #     print("Rejected:", exc)

#     reservation = create_reservation(
#     party_size=4,
#     reservation_date=date(2026, 9, 12),
#     reservation_time=time(23, 0),
#     seating="outdoor",
# )

#     print(reservation)

    # print("\nTEST 1 — 4 people, outdoor, 19:30")
    # result = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(19, 30),
    #     seating="outdoor",
    # )
    # print(result)

    # print("\nTEST 2 — 4 people, indoor, 19:30")
    # result = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(19, 30),
    #     seating="indoor",
    # )
    # print(result)

    # print("\nTEST 3 — 6 people, outdoor, 19:30")
    # result = check_availability(
    #     party_size=6,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(19, 30),
    #     seating="outdoor",
    # )
    # print(result)

    # print("\nTEST 4 — 4 people, outdoor, 20:00")
    # result = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(20, 0),
    #     seating="outdoor",
    # )
    # print(result)

    # print("\nTEST 5 — 8 people, indoor, 19:30")
    # result = check_availability(
    #     party_size=8,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(19, 30),
    #     seating="indoor",
    # )
    # print(result)

    # # existing tests...

    # print("\nTEST 6 — Create reservation")

    # reservation = create_reservation(
    #     reservation_id="R2",
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(20, 0),
    #     seating="outdoor",
    # )

    # print(reservation)

    # print("\nRESERVATIONS:")
    # print(RESERVATIONS)


    # print("\nTEST 7 — Double booking simulation")

    # availability_a = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(21, 30),
    #     seating="outdoor",
    # )

    # availability_b = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(21, 30),
    #     seating="outdoor",
    # )

    # print("Customer A:", availability_a)
    # print("Customer B:", availability_b)
    # # if __name__ == "__main__":

    # result = check_availability(
    #     party_size=4,
    #     reservation_date=date(2026, 9, 12),
    #     reservation_time=time(21, 30),
    #     seating="outdoor",
    # )

    # print(result)

    # # from concurrent.futures import ThreadPoolExecutor

    # # print("\nTEST 8 — Concurrent booking race")

    # # with ThreadPoolExecutor(max_workers=2) as executor:

    #     # future_a = executor.submit(
    #     #     create_reservation_unsafe,
    #     #     "R3",
    #     #     4,
    #     #     date(2026, 9, 12),
    #     #     time(21, 30),
    #     #     "outdoor",
    #     # )

    #     # future_b = executor.submit(
    #     #     create_reservation_unsafe,
    #     #     "R4",
    #     #     4,
    #     #     date(2026, 9, 12),
    #     #     time(21, 30),
    #     #     "outdoor",
    #     # )

    #     # reservation_a = future_a.result()
    #     # reservation_b = future_b.result()

    #     # print("Customer A:", reservation_a)
    #     # print("Customer B:", reservation_b)

    #     # print("\nFINAL RESERVATIONS:")
    #     # for reservation in RESERVATIONS:
    #     #     print(reservation)

    from concurrent.futures import ThreadPoolExecutor