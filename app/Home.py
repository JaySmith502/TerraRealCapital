import sys as _sys, pathlib as _pathlib
for _p in (_pathlib.Path(__file__).resolve(), *_pathlib.Path(__file__).resolve().parents):
    if (_p / "trc").is_dir() and (_p / "ui").is_dir():
        _sys.path.insert(0, str(_p))
        break
import streamlit as st
from ui.auth import require_auth

st.set_page_config(page_title="TRC Research Tool", layout="wide")
require_auth()
st.title("Terra Real Capital — Research Tool")
st.write("Use the sidebar: **Scanner** to generate a report, "
         "**Report Editor** to refine it, **Library** to browse history.")
