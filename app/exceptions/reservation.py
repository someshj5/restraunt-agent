class ReservationConflict(Exception):
    """Raised when a reservation cannot be created because
    the requested table/time is no longer available.
    """

    pass