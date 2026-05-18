import datetime as dt
from typing import Callable


def cached_perplexity(db, *, geo_id: str, scan_date: dt.date, fetch: Callable[[], dict]) -> dict:
    period = scan_date.isoformat()
    hit = db.get_cache(geo_id, period, scan_date)
    if hit is not None:
        return hit
    payload = fetch()
    db.put_cache(geo_id, period, scan_date, payload)
    return payload
