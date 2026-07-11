# youtube_extractor (Simulation)

A small Python module to simulate YouTube Ads campaign data extraction.

This project is for demonstration purposes. It reads predefined CSV templates and applies client-specific parameters (date range, campaign filters, metrics, and output format).

## Suggested Structure

- `data/`: source template CSV files (simulated platform data)
- `configs/`: client request configurations
- `src/youtube_extractor/models/`: config and record models
- `src/youtube_extractor/extractors/`: platform extractor implementation
- `src/youtube_extractor/utils/`: date and CSV utility functions
- `src/youtube_extractor/helpers/`: filter and projection helper functions
- `src/youtube_extractor/`: package entrypoints and backward-compatible imports
- `scripts/`: runnable entry script
- `outputs/`: generated extraction files

## Data Model Idea

Keep a stable base schema for daily campaign performance. Optional extra templates can represent additional slices (device, geography, placement, etc.).

Base daily schema in `data/youtube_campaign_daily_template.csv`:

- `date`
- `client_id`
- `account_id`
- `campaign_id`
- `campaign_name`
- `campaign_status`
- `spend`
- `impressions`
- `views`
- `clicks`
- `conversions`
- `view_rate`
- `ctr`
- `avg_cpv`
- `currency`

## Quick Start

1. Update config values in `configs/client_alpha_last_7_days.json`.
2. Run:

```bash
python scripts/run_extraction.py --config configs/client_alpha_last_7_days.json
```

3. Output CSV will be written to `outputs/`.

## Example Config

```json
{
  "platform": "youtube",
  "dataset": "campaign_daily",
  "client_id": "client_alpha",
  "date_range": {
    "mode": "relative",
    "last_n_days": 7
  },
  "filters": {
    "campaign_status": ["ENABLED"],
    "campaign_ids": []
  },
  "select_columns": [
    "date",
    "client_id",
    "campaign_id",
    "campaign_name",
    "spend",
    "impressions",
    "views",
    "clicks",
    "conversions"
  ],
  "output": {
    "path": "outputs/client_alpha_last_7_days.csv"
  }
}
```

## Notes

- This is intentionally deterministic and local-only.
- No real API calls are made.
- You can add more template files and map them in `extractor.py`.
