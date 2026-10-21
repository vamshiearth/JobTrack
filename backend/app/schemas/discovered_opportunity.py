from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredOpportunity:
    source: str
    source_board: str
    source_job_id: str
    company_name: str
    job_title: str
    location: str | None
    source_url: str
    description: str | None
