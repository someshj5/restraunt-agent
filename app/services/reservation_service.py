from datetime import date, datetime, time, timedelta
from uuid import uuid4

import psycopg

from app.db.connection import get_connection
from app.exceptions.reservation import ReservationConflict
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.reservation import Reservation
from app.utils.fingerprints import build_request_fingerprint


RESERVATION_DURATION = timedelta(minutes=90)


class ReservationService:

    def __init__(self):
        self.repository = ReservationRepository()

    def check_availability(self,party_size: int,reservation_date: date,reservation_time: time,seating: str | None = None,) -> bool:

        requested_start = datetime.combine(
            reservation_date,
            reservation_time,
        )

        requested_end = requested_start + RESERVATION_DURATION

        with get_connection() as conn:

            table_id = self.repository.find_available_table(
                conn=conn,
                party_size=party_size,
                seating=seating,
                requested_start=requested_start,
                requested_end=requested_end,
            )

            return table_id is not None
    

    def create_reservation(
        self,
        party_size: int,
        reservation_date: date,
        reservation_time: time,
        seating: str | None = None,
        idempotency_key: str | None = None,
    ) -> Reservation:

        # ---------------------------------------------------------
        # 1. Calculate reservation interval
        # ---------------------------------------------------------

        requested_start = datetime.combine(
            reservation_date,
            reservation_time,
        )

        requested_end = requested_start + RESERVATION_DURATION

        # ---------------------------------------------------------
        # 2. Build deterministic request fingerprint
        # ---------------------------------------------------------

        fingerprint = build_request_fingerprint(
            party_size=party_size,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            seating=seating,
        )

        # ---------------------------------------------------------
        # 3. Open ONE database connection
        # ---------------------------------------------------------

        with get_connection() as conn:

            # =====================================================
            # 4. Fast-path idempotency check
            # =====================================================

            if idempotency_key is not None:

                existing = (
                    self.repository.find_by_idempotency_key(
                        conn,
                        idempotency_key,
                    )
                )

                if existing:

                    # Same key, different request
                    if existing[5] != fingerprint:
                        raise ValueError(
                            "Idempotency key was already used "
                            "for a different reservation request."
                        )

                    # Same key, same request
                    return self._to_reservation(existing)

            # =====================================================
            # 5. Find available table
            # =====================================================

            table_id = self.repository.find_available_table(
                conn=conn,
                party_size=party_size,
                seating=seating,
                requested_start=requested_start,
                requested_end=requested_end,
            )

            if table_id is None:
                raise ReservationConflict(
                    "No table is available for the requested time."
                )

            # =====================================================
            # 6. Create reservation
            #
            # The nested transaction acts as a SAVEPOINT.
            #
            # If INSERT fails, only the SAVEPOINT is rolled back,
            # allowing us to continue using the outer connection.
            # =====================================================

            try:

                with conn.transaction():

                    result = self.repository.create(
                        conn=conn,
                        reservation_id=uuid4(),
                        table_id=table_id,
                        party_size=party_size,
                        requested_start=requested_start,
                        requested_end=requested_end,
                        idempotency_key=idempotency_key,
                        fingerprint=fingerprint,
                    )

            except psycopg.errors.UniqueViolation:

                # =================================================
                # 7. Another concurrent request may have created
                #    the same idempotency key.
                #
                # The nested transaction has already rolled back
                # its SAVEPOINT, so the connection is usable again.
                # =================================================

                if idempotency_key is None:
                    raise

                existing = (
                    self.repository.find_by_idempotency_key(
                        conn,
                        idempotency_key,
                    )
                )

                if existing is None:
                    # The UniqueViolation was caused by some
                    # unexpected unique constraint.
                    raise

                # Same key but different request
                if existing[5] != fingerprint:
                    raise ValueError(
                        "Idempotency key was already used "
                        "for a different reservation request."
                    )

                # Same request → return the reservation created
                # by the other concurrent request.
                return self._to_reservation(existing)

            except psycopg.errors.ExclusionViolation as exc:

                # Another request won the table race.
                raise ReservationConflict(
                    "The selected table is no longer available."
                ) from exc

            # =====================================================
            # 8. Convert database result to domain model
            # =====================================================

            return self._to_reservation(result)

    # =============================================================
    # Database row → Pydantic domain model
    # =============================================================

    @staticmethod
    def _to_reservation(row) -> Reservation:

        return Reservation(
            id=str(row[0]),
            table_id=str(row[1]),
            party_size=row[2],
            date=row[3].date(),
            start=row[3].time(),
            end=row[4].time(),
        )