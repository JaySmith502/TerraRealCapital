import sys as _sys, pathlib as _pathlib
for _p in (_pathlib.Path(__file__).resolve(), *_pathlib.Path(__file__).resolve().parents):
    if (_p / "trc").is_dir() and (_p / "ui").is_dir():
        _sys.path.insert(0, str(_p))
        break
import streamlit as st
from ui.auth import require_auth
from ui.resources import database

st.set_page_config(page_title="Library", layout="wide")
require_auth()
st.title("Library")

db = database()
reports = db.list_reports()
cities = {c["id"]: f'{c["name"]}, {c["state"]}' for c in db.list_cities()}

if not reports:
    st.info("No reports yet. Run one from the Scanner.")
    st.stop()

c1, c2, c3 = st.columns(3)
city_filter = c1.selectbox("City", ["All"] + sorted(set(cities.values())))
status_filter = c2.selectbox("Status", ["All", "ready", "edited"])
tag_filter = c3.text_input("Tag contains")

def keep(r):
    if city_filter != "All" and cities.get(r["city_id"]) != city_filter:
        return False
    if status_filter != "All" and r.get("status") != status_filter:
        return False
    if tag_filter and not any(tag_filter.lower() in t.lower()
                              for t in (r.get("tags") or [])):
        return False
    return True

rows = [r for r in reports if keep(r)]
st.caption(f"{len(rows)} report(s)")
for r in rows:
    with st.container(border=True):
        st.markdown(f'**{cities.get(r["city_id"], "?")}** · {r["scan_date"]} '
                    f'· `{r.get("status")}` · {", ".join(r.get("tags") or [])}')
        if st.button("Open in editor", key=f'open-{r["id"]}'):
            st.session_state["open_report_id"] = r["id"]
            st.switch_page("pages/2_Report_Editor.py")
