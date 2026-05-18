import pytest
from trc.config import Settings

def test_settings_reads_required_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pk")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.setenv("APP_PASSWORD", "hunter2")
    s = Settings()
    assert s.supabase_url == "https://x.supabase.co"
    assert s.app_password == "hunter2"

def test_settings_missing_required_raises(monkeypatch):
    for k in ["SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","PERPLEXITY_API_KEY","ANTHROPIC_API_KEY","APP_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(Exception):
        Settings()
