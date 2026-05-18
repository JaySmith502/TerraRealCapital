import datetime as dt
import streamlit as st
from ui.auth import require_auth
from ui.resources import database, anthropic_client, settings
from trc.orchestrator import scan
from trc.perplexity import research_city
from trc.claude import generate_report

st.set_page_config(page_title="Scanner", layout="wide")
require_auth()
st.title("Scanner")

db = database()
cities = db.list_cities()
by_label = {f'{c["name"]}, {c["state"]}': c for c in cities}

label = st.selectbox("City", list(by_label))
SIGNALS = ["jobs", "population", "rents", "supply pipeline",
           "capital flows", "submarkets"]
chosen = st.multiselect("Emphasise signals (optional)", SIGNALS)

if st.button("Scan", type="primary"):
    city = by_label[label]
    cfg = settings()
    today = dt.date.today()
    try:
        with st.status("Starting scan…", expanded=True) as status:
            def progress(msg: str):
                status.update(label=msg)
                st.write(msg)

            rid = scan(
                db,
                city=city,
                signals=chosen,
                scan_date=today,
                perplexity_fetch=lambda: research_city(
                    api_key=cfg.perplexity_api_key,
                    model=cfg.perplexity_model,
                    city_name=city["name"], state=city["state"],
                    signals=chosen),
                claude_generate=lambda research: generate_report(
                    anthropic_client(), model=cfg.claude_model,
                    research_text=research, signals=chosen),
                progress=progress,
            )
            status.update(label="Scan complete", state="complete")
        st.session_state["open_report_id"] = rid
        st.success("Report ready. Open it from **Report Editor** in the sidebar.")
    except Exception as e:  # noqa: BLE001 - top-level scan boundary
        # st.status auto-marks error when the with-block raises; reinforce with a banner.
        # Spec §5: human-readable banner in the UI; full traceback server-side ONLY
        # (never st.exception()). Streamlit Community Cloud captures stdout/stderr.
        import logging
        logging.exception("scan failed")
        st.error(f"Scan failed ({type(e).__name__}): {e}")
