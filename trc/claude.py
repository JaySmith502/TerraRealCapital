from anthropic import Anthropic
from trc.config import Settings
from trc.models import ReportPayload
from trc.prompts.system import SCAN_SYSTEM_PROMPT, EMIT_REPORT_TOOL


def make_anthropic(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def generate_report(client, *, model: str, research_text: str,
                    signals: list[str]) -> ReportPayload:
    focus = f"\n\nEmphasise: {', '.join(signals)}." if signals else ""
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=[{
            "type": "text",
            "text": SCAN_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[EMIT_REPORT_TOOL],
        tool_choice={"type": "tool", "name": "emit_report"},
        messages=[{
            "role": "user",
            "content": f"Research to convert into the report:\n\n{research_text}{focus}",
        }],
    )
    tool_use = next(b for b in msg.content if getattr(b, "type", None) == "tool_use")
    return ReportPayload.model_validate(tool_use.input)
