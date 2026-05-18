from trc.claude import generate_report
from trc.models import ReportPayload
from trc.prompts.system import SCAN_SYSTEM_PROMPT


class FakeBlock:
    def __init__(self, **kw): self.__dict__.update(kw)


class FakeMessages:
    def __init__(self, captured): self.captured = captured

    def create(self, **kw):
        self.captured.update(kw)
        tool_block = FakeBlock(type="tool_use", name="emit_report", input={
            "metrics": {"pop": "1.2M"}, "signals": {}, "capital_flows": {},
            "submarkets": {}, "evidence": [], "metrics_extra": {},
            "narrative_markdown": "## Market Overview\n\nText.",
        })
        return FakeBlock(content=[tool_block],
                         usage=FakeBlock(cache_read_input_tokens=0))


class FakeAnthropic:
    def __init__(self): self.captured = {}; self.messages = FakeMessages(self.captured)


def test_generate_report_forces_tool_and_caches_system():
    client = FakeAnthropic()
    payload = generate_report(client, model="claude-sonnet-4-6",
                              research_text="raw research", signals=["jobs"])
    assert isinstance(payload, ReportPayload)
    assert payload.metrics == {"pop": "1.2M"}
    sys = client.captured["system"]
    assert isinstance(sys, list) and sys[0]["cache_control"] == {"type": "ephemeral"}
    assert client.captured["tool_choice"] == {"type": "tool", "name": "emit_report"}
    # headroom for long narrative + structured buckets (real-API truncation fix)
    assert client.captured["max_tokens"] >= 16000


def test_scan_system_prompt_is_real_and_cacheable():
    assert len(SCAN_SYSTEM_PROMPT) > 4000
    assert "[Extend" not in SCAN_SYSTEM_PROMPT
    assert "TODO" not in SCAN_SYSTEM_PROMPT


def test_regenerate_section_returns_plain_body():
    from trc.claude import regenerate_section
    class M:
        def create(self, **kw):
            self.kw = kw
            return FakeBlock(content=[FakeBlock(type="text", text="Punchier body.")],
                             usage=FakeBlock(cache_read_input_tokens=0))
    class C: messages = M()
    c = C()
    out = regenerate_section(c, model="claude-sonnet-4-6",
                             section_title="Beta", section_body="Old body",
                             instruction="make it punchier")
    assert out == "Punchier body."
