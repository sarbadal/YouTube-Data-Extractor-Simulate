from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CampaignRecord:
    """Typed representation of one campaign-level performance record.

    This model mirrors the base daily campaign template schema and offers a
    structured object instead of passing raw dictionaries across the codebase.
    All fields are strings because CSV inputs are text-based in this simulator.
    """

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
        """Build a ``CampaignRecord`` from a CSV row dictionary.

        The helper converts a raw ``DictReader`` row into a typed dataclass
        instance while safely handling missing keys by defaulting to empty
        strings. This keeps downstream code resilient when template schemas
        evolve or when optional columns are absent.

        Args:
            row: One raw row from a template CSV, keyed by column name.

        Returns:
            A populated ``CampaignRecord`` instance.
        """
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
