from supabase import create_client
from trc.config import Settings


def make_client(settings: Settings):
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class Database:
    def __init__(self, client):
        self.c = client

    def insert_report(self, row: dict) -> str:
        res = self.c.table("reports").insert(row).execute()
        return res.data[0]["id"]

    def get_report(self, report_id: str) -> dict | None:
        res = self.c.table("reports").select("*").eq("id", report_id).execute()
        return res.data[0] if res.data else None

    def list_reports(self) -> list[dict]:
        return self.c.table("reports").select("*").order("scan_date", desc=True).execute().data

    def update_report(self, report_id: str, patch: dict) -> None:
        self.c.table("reports").update(patch).eq("id", report_id).execute()

    def list_cities(self) -> list[dict]:
        return self.c.table("cities").select("*").order("name").execute().data

    def get_cache(self, source, geo_id, period, fetched_on) -> dict | None:
        fetched_on_str = fetched_on.isoformat() if hasattr(fetched_on, "isoformat") else fetched_on
        res = (self.c.table("api_cache").select("payload")
               .eq("source", source).eq("geo_id", geo_id)
               .eq("period", period).eq("fetched_on", fetched_on_str).execute())
        return res.data[0]["payload"] if res.data else None

    def put_cache(self, source, geo_id, period, fetched_on, payload) -> None:
        fetched_on_str = fetched_on.isoformat() if hasattr(fetched_on, "isoformat") else fetched_on
        self.c.table("api_cache").insert({
            "source": source, "geo_id": geo_id, "period": period,
            "fetched_on": fetched_on_str, "payload": payload,
        }).execute()
