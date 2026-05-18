import sys as _sys, pathlib as _pathlib
for _p in (_pathlib.Path(__file__).resolve(), *_pathlib.Path(__file__).resolve().parents):
    if (_p / "trc").is_dir() and (_p / "ui").is_dir():
        _sys.path.insert(0, str(_p))
        break
import datetime as dt
import streamlit as st
from ui.auth import require_auth
from ui.resources import database, anthropic_client, settings
from ui.structured_panel import render_structured_panel
from trc.narrative import section_titles, split_sections, splice_section
from trc.claude import regenerate_section

st.set_page_config(page_title="Report Editor", layout="wide")
require_auth()
st.title("Report Editor")

db = database()
reports = db.list_reports()
if not reports:
    st.info("No reports yet. Run one from the Scanner.")
    st.stop()

labels = {f'{r["scan_date"]} · {r["id"][:8]} · {r.get("status")}': r["id"]
          for r in reports}
default_id = st.session_state.get("open_report_id")
keys = list(labels)
idx = next((i for i, k in enumerate(keys) if labels[k] == default_id), 0)
sel = st.selectbox("Report", keys, index=idx)
report = db.get_report(labels[sel])

# Per-report edit buffer in session
buf_key = f"narr::{report['id']}"
if buf_key not in st.session_state:
    st.session_state[buf_key] = report.get("narrative_edited") or ""

left, right = st.columns(2)
with left:
    st.subheader("Structured")
    render_structured_panel(report)
with right:
    st.subheader("Narrative")
    st.session_state[buf_key] = st.text_area(
        "Markdown", st.session_state[buf_key], height=480, label_visibility="collapsed")
    st.markdown("**Preview**")
    st.markdown(st.session_state[buf_key])

st.divider()
st.subheader("Regenerate a section")
titles = section_titles(st.session_state[buf_key])
if titles:
    tcol, icol, bcol = st.columns([2, 3, 1])
    target = tcol.selectbox("Section", titles)
    instruction = icol.text_input("Instruction (optional)",
                                  placeholder="make it punchier")
    if bcol.button("Regenerate"):
        _, secs = split_sections(st.session_state[buf_key])
        body = next(s.body for s in secs if s.title == target)
        new_body = regenerate_section(
            anthropic_client(), model=settings().claude_model,
            section_title=target, section_body=body, instruction=instruction)
        st.session_state[buf_key] = splice_section(
            st.session_state[buf_key], target, new_body)
        st.rerun()
else:
    st.caption("No `##` sections detected to regenerate.")

st.divider()
tags = st.text_input("Tags (comma-separated)",
                     ", ".join(report.get("tags") or []))
if st.button("Save", type="primary"):
    db.update_report(report["id"], {
        "narrative_edited": st.session_state[buf_key],
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "status": "edited",
        "edited_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })
    st.success("Saved.")
    st.rerun()

st.divider()
st.subheader("Copy for Beehiiv")
st.code(st.session_state[buf_key], language="markdown")
