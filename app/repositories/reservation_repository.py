from datetime import datetime

from uuid import UUID


        
class ReservationRepository:

    def find_by_idempotency_key(
        self,
        conn,
        idempotency_key: str,
    ):
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

            return cursor.fetchone()

    def find_available_table(
        self,
        conn,
        party_size: int,
        seating: str | None,
        requested_start: datetime,
        requested_end: datetime,
    ):

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
            cursor.execute(
                query,
                params,
            )

            row = cursor.fetchone()

            return row[0] if row else None

    def create(
        self,
        conn,
        reservation_id: UUID,
        table_id: UUID,
        party_size: int,
        requested_start: datetime,
        requested_end: datetime,
        idempotency_key: str | None,
        fingerprint: str,
    ):

        with conn.cursor() as cursor:

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

            return cursor.fetchone()

     
        