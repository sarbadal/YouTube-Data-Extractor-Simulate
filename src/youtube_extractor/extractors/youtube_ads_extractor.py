from __future__ import annotations

from pathlib import Path

from youtube_extractor.helpers import filter_rows, project_columns
from youtube_extractor.models import load_config
from youtube_extractor.utils import load_rows, write_output

DATASET_TO_FILE = {
    "campaign_daily": "youtube_campaign_daily_template.csv",
    "campaign_device": "youtube_campaign_device_template.csv",
    "campaign_geo": "youtube_campaign_geo_template.csv",
    "campaign_placement": "youtube_campaign_placement_template.csv",
    "campaign_audience": "youtube_audience_template.csv",
    "campaign_adgroup": "youtube_adgroup_template.csv",
    "campaign_ads": "youtube_ads_template.csv",
}


def run_extraction(config_path: str | Path, project_root: str | Path | None = None) -> Path:
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[3]

    config = load_config(config_path)
    if config.platform.lower() != "youtube":
        raise ValueError("This simulator currently supports only platform='youtube'")

    dataset_file = DATASET_TO_FILE.get(config.dataset)
    if not dataset_file:
        raise ValueError(f"Unsupported dataset: {config.dataset}")

    source_path = root / "data" / dataset_file
    rows = load_rows(source_path)
    rows = filter_rows(rows, config)
    rows = project_columns(rows, config.select_columns)

    output_path = root / config.output.get("path", "outputs/extraction.csv")
    write_output(rows, output_path, config.select_columns)
    return output_path
