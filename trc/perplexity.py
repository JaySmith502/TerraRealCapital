import httpx

ENDPOINT = "https://api.perplexity.ai/chat/completions"


def _prompt(city_name: str, state: str, signals: list[str]) -> str:
    focus = f" Emphasise these signals: {', '.join(signals)}." if signals else ""
    return (
        f"Research the multifamily real-estate investment outlook for "
        f"{city_name}, {state}. Cover population and migration, employment and "
        f"major employers, rent and vacancy trends, multifamily construction "
        f"pipeline, notable capital flows and federal awards, and submarket "
        f"dynamics. Cite recent, specific sources.{focus}"
    )


def research_city(*, api_key: str, model: str, city_name: str, state: str,
                  signals: list[str], timeout: float = 90.0) -> dict:
    resp = httpx.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user",
                          "content": _prompt(city_name, state, signals)}],
            "search_recency_filter": "month",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "citations": data.get("citations", []),
        "search_results": data.get("search_results", []),
    }
