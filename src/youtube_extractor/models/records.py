from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CampaignRecord:
    date: str
    client_id: str
    account_id: str
    campaign_id: str
    campaign_name: str
    campaign_status: str
    spend: str
    impressions: str
    views: str
    clicks: str
    conversions: str
    view_rate: str
    ctr: str
    avg_cpv: str
    currency: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "CampaignRecord":
        return cls(
            date=row.get("date", ""),
            client_id=row.get("client_id", ""),
            account_id=row.get("account_id", ""),
            campaign_id=row.get("campaign_id", ""),
            campaign_name=row.get("campaign_name", ""),
            campaign_status=row.get("campaign_status", ""),
            spend=row.get("spend", ""),
            impressions=row.get("impressions", ""),
            views=row.get("views", ""),
            clicks=row.get("clicks", ""),
            conversions=row.get("conversions", ""),
            view_rate=row.get("view_rate", ""),
            ctr=row.get("ctr", ""),
            avg_cpv=row.get("avg_cpv", ""),
            currency=row.get("currency", ""),
        )
