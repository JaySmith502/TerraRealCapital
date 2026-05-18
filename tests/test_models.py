from trc.models import City, ReportPayload, ScanRequest


def test_report_payload_requires_narrative_and_buckets():
    p = ReportPayload(
        metrics={"population": "1.2M (per source)"},
        signals={"jobs": "growing"},
        capital_flows={"federal": "award X"},
        submarkets={"downtown": "tight"},
        evidence=[{"claim": "x", "source": "https://a"}],
        metrics_extra={},
        narrative_markdown="# Title\n\nBody",
    )
    assert p.narrative_markdown.startswith("# Title")


def test_scan_request_defaults_signals_empty():
    r = ScanRequest(city_id="abc")
    assert r.toggled_signals == []
