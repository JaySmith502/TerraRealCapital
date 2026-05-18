from pydantic import BaseModel, Field


class City(BaseModel):
    id: str
    name: str
    state: str
    fips_county: str
    fips_metro: str


class ScanRequest(BaseModel):
    city_id: str
    toggled_signals: list[str] = Field(default_factory=list)


class ReportPayload(BaseModel):
    """The dual-output Claude must produce (enforced via forced tool-use)."""
    metrics: dict = Field(default_factory=dict)
    signals: dict = Field(default_factory=dict)
    capital_flows: dict = Field(default_factory=dict)
    submarkets: dict = Field(default_factory=dict)
    evidence: list = Field(default_factory=list)
    metrics_extra: dict = Field(default_factory=dict)
    narrative_markdown: str
