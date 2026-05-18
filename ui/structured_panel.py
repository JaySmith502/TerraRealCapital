import streamlit as st

def _kv(title: str, obj):
    if not obj:
        return
    st.subheader(title)
    if isinstance(obj, dict):
        for k, v in obj.items():
            st.markdown(f"- **{k}:** {v}")
    else:
        st.json(obj)

def render_structured_panel(report: dict) -> None:
    _kv("Metrics", report.get("metrics"))
    _kv("Signals", report.get("signals"))
    _kv("Capital flows", report.get("capital_flows"))
    _kv("Submarkets", report.get("submarkets"))
    _kv("Evidence", report.get("evidence"))
    _kv("Other metrics", report.get("metrics_extra"))
