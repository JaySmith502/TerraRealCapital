import datetime as dt
from typing import Callable
from trc.cache import cached_perplexity
from trc.models import ReportPayload

def scan(db, *, city: dict, signals: list[str], scan_date: dt.date,
         perplexity_fetch: Callable[[], dict],
         claude_generate: Callable[[str], ReportPayload],
         progress: Callable[[str], None]) -> str:
    progress("Researching via Perplexity…")
    research = cached_perplexity(db, geo_id=city["fips_metro"],
                                 scan_date=scan_date, fetch=perplexity_fetch)

    progress("Writing report with Claude…")
    payload: ReportPayload = claude_generate(research["content"])

    progress("Saving…")
    row = {
        "city_id": city["id"],
        "scan_date": scan_date.isoformat(),
        "status": "ready",
        "toggled_signals": signals,
        "metrics": payload.metrics,
        "signals": payload.signals,
        "capital_flows": payload.capital_flows,
        "submarkets": payload.submarkets,
        "evidence": payload.evidence,
        "metrics_extra": payload.metrics_extra,
        "narrative_raw": payload.narrative_markdown,
        "narrative_edited": payload.narrative_markdown,
    }
    return db.insert_report(row)
