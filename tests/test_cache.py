import datetime as dt
from trc.cache import cached_perplexity


def test_cache_miss_calls_fetcher_then_stores():
    calls = []
    store = {}
    class DB:
        def get_cache(s,g,p,f): return None
        def put_cache(s,g,p,f,payload): store["v"] = payload
    def fetch(): calls.append(1); return {"content": "fresh"}
    out = cached_perplexity(DB(), geo_id="26163", scan_date=dt.date(2026,5,18), fetch=fetch)
    assert out == {"content": "fresh"}
    assert calls == [1] and store["v"] == {"content": "fresh"}


def test_cache_hit_skips_fetcher():
    class DB:
        def get_cache(s,g,p,f): return {"content": "cached"}
        def put_cache(*a, **k): raise AssertionError("should not write")
    out = cached_perplexity(DB(), geo_id="26163", scan_date=dt.date(2026,5,18),
                            fetch=lambda: (_ for _ in ()).throw(AssertionError("no call")))
    assert out == {"content": "cached"}
