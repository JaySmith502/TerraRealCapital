import streamlit as st
from trc.config import Settings
from trc.db import Database, make_client
from trc.claude import make_anthropic

@st.cache_resource
def settings() -> Settings:
    import os
    for k in ["SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","PERPLEXITY_API_KEY",
              "ANTHROPIC_API_KEY","APP_PASSWORD"]:
        os.environ.setdefault(k, st.secrets[k])
    return Settings()

@st.cache_resource
def database() -> Database:
    return Database(make_client(settings()))

@st.cache_resource
def anthropic_client():
    return make_anthropic(settings())
