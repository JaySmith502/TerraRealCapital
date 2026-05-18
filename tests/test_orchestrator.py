import datetime as dt, pytest
from trc.orchestrator import scan
from trc.models import ReportPayload

class DB:
    def __init__(self): self.inserted=None; self.cache={}
    def get_cache(self,*a): return None
    def put_cache(self,*a): pass
    def insert_report(self, row): self.inserted=row; return "rid-1"

def good_payload():
    return ReportPayload(metrics={"p":"1"}, signals={}, capital_flows={},
        submarkets={}, evidence=[], metrics_extra={},
        narrative_markdown="## Market Overview\n\nText.")

def test_scan_happy_path_persists_once_and_reports_progress():
    db = DB(); steps=[]
    rid = scan(db,
        city={"id":"c1","name":"Detroit","state":"MI","fips_metro":"19820"},
        signals=["jobs"], scan_date=dt.date(2026,5,18),
        perplexity_fetch=lambda: {"content":"raw","citations":["u"],"search_results":[]},
        claude_generate=lambda research: good_payload(),
        progress=steps.append)
    assert rid == "rid-1"
    assert db.inserted["status"] == "ready"
    assert db.inserted["narrative_raw"] == db.inserted["narrative_edited"]
    assert "Researching" in steps[0]

def test_scan_failure_persists_nothing():
    db = DB()
    def boom(): raise RuntimeError("perplexity down")
    with pytest.raises(RuntimeError):
        scan(db, city={"id":"c1","name":"X","state":"MI","fips_metro":"00000"},
             signals=[], scan_date=dt.date(2026,5,18),
             perplexity_fetch=boom, claude_generate=lambda r: good_payload(),
             progress=lambda s: None)
    assert db.inserted is None
