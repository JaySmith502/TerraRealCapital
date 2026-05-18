import datetime
import json

from trc.db import Database


class FakeTable:
    def __init__(self, store, name): self.store, self.name, self._q = store, name, {}
    def insert(self, row): self._row = row; return self
    def update(self, patch): self._patch = patch; return self
    def select(self, *_): self._op = "select"; return self
    def eq(self, k, v): self._q[k] = v; return self
    def order(self, *_a, **_k): return self
    def execute(self):
        if getattr(self, "_row", None) is not None:
            rec = {**self._row, "id": "r1"}; self.store[self.name].append(rec)
            return type("R", (), {"data": [rec]})
        if getattr(self, "_patch", None) is not None:
            for r in self.store[self.name]:
                if all(r.get(k) == v for k, v in self._q.items()):
                    r.update(self._patch)
            return type("R", (), {"data": []})
        rows = [r for r in self.store[self.name]
                if all(r.get(k) == v for k, v in self._q.items())]
        return type("R", (), {"data": rows})


class FakeClient:
    def __init__(self): self.store = {"reports": [], "cities": []}
    def table(self, n): return FakeTable(self.store, n)


def test_insert_and_get_report():
    db = Database(FakeClient())
    rid = db.insert_report({"city_id": "c1", "narrative_raw": "x"})
    assert rid == "r1"
    got = db.get_report("r1")
    assert got["narrative_raw"] == "x"


def test_list_reports_returns_rows():
    db = Database(FakeClient())
    db.insert_report({"city_id": "c1"})
    assert len(db.list_reports()) == 1


def test_update_report_writes_patch():
    db = Database(FakeClient())
    rid = db.insert_report({"city_id": "c1", "status": "ready", "narrative_raw": "original"})
    db.update_report(rid, {"status": "edited", "narrative_edited": "new text"})
    got = db.get_report(rid)
    assert got["status"] == "edited"
    assert got["narrative_edited"] == "new text"
    assert got["narrative_raw"] == "original"  # unrelated field unchanged


# --- cache serialization regression tests ---

class SerializingFakeTable:
    """FakeTable that json.dumps the inserted row to catch non-serializable values."""
    def __init__(self): self._rows = []; self._eq_args = {}
    def insert(self, row):
        json.dumps(row)   # raises TypeError if row contains non-serializable values
        self._rows.append(row)
        return self
    def select(self, *_): return self
    def eq(self, k, v): self._eq_args[k] = v; return self
    def execute(self): return type("R", (), {"data": self._rows})


class SerializingFakeClient:
    def __init__(self): self._table = SerializingFakeTable()
    def table(self, _): return self._table


def test_put_cache_row_is_json_serializable():
    client = SerializingFakeClient()
    db = Database(client)
    d = datetime.date(2026, 5, 18)
    # Should not raise TypeError; fetched_on must be stored as ISO string
    db.put_cache("perplexity", "19820", "2026-05-18", d, {"k": "v"})
    row = client._table._rows[0]
    assert row["fetched_on"] == "2026-05-18"


def test_get_cache_normalizes_date_filter():
    client = SerializingFakeClient()
    db = Database(client)
    d = datetime.date(2026, 5, 18)
    db.get_cache("perplexity", "19820", "2026-05-18", d)
    assert client._table._eq_args["fetched_on"] == "2026-05-18"
