import pytest

@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    # Ensure tests never read the developer's real .env
    monkeypatch.chdir(tmp_path)
