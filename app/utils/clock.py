from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_datetime(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))

if __name__ == "__main__":
    now = get_current_datetime("Asia/Kolkata")
    print(f"now:{now}")