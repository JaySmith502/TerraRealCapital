import hmac
import streamlit as st

def password_matches(entered: str, expected: str) -> bool:
    return hmac.compare_digest(entered or "", expected or "")

def require_auth() -> None:
    """Call at the top of every page/entrypoint. Blocks until authed."""
    if st.session_state.get("authed"):
        return
    st.title("Terra Real Capital — Research Tool")
    pw = st.text_input("Password", type="password")
    if st.button("Enter"):
        if password_matches(pw, st.secrets["APP_PASSWORD"]):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
