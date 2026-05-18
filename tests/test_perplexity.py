import httpx, respx
from trc.perplexity import research_city


@respx.mock
def test_research_city_posts_and_parses():
    route = respx.post("https://api.perplexity.ai/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "Detroit multifamily brief..."}}],
            "citations": ["https://a.com", "https://b.com"],
            "search_results": [{"title": "T", "url": "https://a.com", "date": "2026-05-01"}],
        })
    )
    out = research_city(api_key="pk", model="sonar-pro",
                         city_name="Detroit", state="MI", signals=["jobs"])
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer pk"
    assert out["content"].startswith("Detroit")
    assert out["citations"] == ["https://a.com", "https://b.com"]
    assert out["search_results"][0]["url"] == "https://a.com"


@respx.mock
def test_research_city_raises_on_http_error():
    respx.post("https://api.perplexity.ai/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"}))
    import pytest
    with pytest.raises(httpx.HTTPStatusError):
        research_city(api_key="pk", model="sonar-pro",
                      city_name="Detroit", state="MI", signals=[])
