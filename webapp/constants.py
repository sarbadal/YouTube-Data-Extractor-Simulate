from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
CONFIG_OUTPUT_DIR = PROJECT_ROOT / "configs" / "generated"
SECRET_KEY = "youtube-extractor-demo-secret"

DATASET_OPTIONS = [
    "campaign_daily",
    "campaign_device",
    "campaign_geo",
    "campaign_placement",
    "campaign_audience",
    "campaign_adgroup",
    "campaign_ads",
]

DATASET_DEFAULT_COLUMNS: dict[str, list[str]] = {
    "campaign_daily": [
        "date",
        "client_id",
        "campaign_id",
        "campaign_name",
        "campaign_status",
        "spend",
        "impressions",
        "views",
        "clicks",
        "conversions",
    ],
    "campaign_device": [
        "date",
        "client_id",
        "campaign_id",
        "device",
        "impressions",
        "views",
        "clicks",
        "spend",
    ],
    "campaign_geo": [
        "date",
        "client_id",
        "campaign_id",
        "country",
        "region",
        "impressions",
        "views",
        "clicks",
        "spend",
        "conversions",
    ],
    "campaign_placement": [
        "date",
        "client_id",
        "campaign_id",
        "placement_type",
        "impressions",
        "views",
        "clicks",
        "spend",
    ],
    "campaign_audience": [
        "date",
        "client_id",
        "campaign_id",
        "audience_segment",
        "audience_type",
        "impressions",
        "views",
        "clicks",
        "spend",
        "conversions",
    ],
    "campaign_adgroup": [
        "date",
        "client_id",
        "campaign_id",
        "adgroup_id",
        "adgroup_name",
        "adgroup_status",
        "impressions",
        "views",
        "clicks",
        "spend",
        "conversions",
    ],
    "campaign_ads": [
        "date",
        "client_id",
        "campaign_id",
        "adgroup_id",
        "ad_id",
        "ad_name",
        "ad_format",
        "ad_status",
        "impressions",
        "views",
        "clicks",
        "spend",
        "conversions",
    ],
}
