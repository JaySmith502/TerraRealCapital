import streamlit as st
from ui.auth import require_auth

st.set_page_config(page_title="TRC Research Tool", layout="wide")
require_auth()
st.title("Terra Real Capital — Research Tool")
st.write("Use the sidebar: **Scanner** to generate a report, "
         "**Report Editor** to refine it, **Library** to browse history.")
