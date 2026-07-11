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
    """Run a simulated YouTube Ads data extraction using a config file.

    This function is the main orchestration entrypoint for the extractor module.
    It reads a JSON config, validates platform and dataset, loads the mapped
    template CSV from ``data/``, applies filters/column projection, and writes
    the final report CSV to the configured output path.

    The extraction is fully local and deterministic. No network/API calls are
    made. It is intended for demos and development workflows where the output
    schema should mimic a real platform extraction flow.

    Args:
        config_path: Path to the extraction config JSON. The config must include
            values such as ``platform``, ``dataset``, ``client_id``,
            ``date_range``, ``filters``, ``select_columns``, and ``output``.
        project_root: Optional repository root path. When omitted, the function
            auto-detects it from this file location.

    Returns:
        Path to the generated output CSV file.

    Raises:
        ValueError: If the platform is not ``youtube`` or if the dataset key is
            not supported by ``DATASET_TO_FILE``.
        FileNotFoundError: If the mapped source template file is missing.
        json.JSONDecodeError: If the config file contains invalid JSON.
        OSError: If writing the output file fails.
    """
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
