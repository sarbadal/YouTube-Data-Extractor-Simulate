# YouTube Ads Extraction Simulator - Usage Steps

This guide explains how to run a simulated YouTube Ads data extraction using config-driven parameters.

## 1) Prepare your config file

Open:

- `configs/client_alpha_last_7_days.json`

Set the fields you need:

- `platform`: must be `youtube`
- `dataset`: `campaign_daily` or `campaign_device`
- `client_id`: the client you want to extract for
- `date_range`: relative or explicit date window
- `filters`: optional campaign filters
- `select_columns`: columns to include in output
- `output.path`: output CSV destination

Example (relative last 7 days):

```json
{
  "platform": "youtube",
  "dataset": "campaign_daily",
  "client_id": "client_alpha",
  "date_range": {
    "mode": "relative",
    "last_n_days": 7,
    "anchor_date": "2026-07-11"
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
    "campaign_status",
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

## 2) Run the extraction script

From project root:

```bash
/usr/bin/python3 scripts/run_extraction.py --config configs/client_alpha_last_7_days.json
```

## 3) Read the extracted CSV

The output file is written to the `output.path` in your config.

For the sample config above:

- `outputs/client_alpha_last_7_days.csv`

## Optional: Explicit date range

Use this in config if you want fixed dates:

```json
"date_range": {
  "mode": "explicit",
  "start_date": "2026-07-01",
  "end_date": "2026-07-07"
}
```

## Optional: Device-level extraction

Set dataset to:

- `campaign_device`

What this means:

- Instead of overall campaign totals, the extractor returns campaign metrics split by device type.
- Typical device values are `MOBILE`, `DESKTOP`, and `TV`.
- Each row usually represents one `date + campaign_id + device` combination.

What changes internally:

- The extractor switches the source template to `data/youtube_campaign_device_template.csv`.
- Your normal filters still apply (`client_id`, `date_range`, and optional `campaign_ids`).
- `select_columns` still controls exactly which columns appear in the output CSV.

Why use it:

- Use this when you want a device breakdown for analysis or demos (for example, how much performance came from mobile vs TV).
- Keep using `campaign_daily` when you only need overall daily campaign performance.

And choose columns matching:

- `data/youtube_campaign_device_template.csv`

Example config (`configs/client_alpha_device_last_7_days.json`):

```json
{
  "platform": "youtube",
  "dataset": "campaign_device",
  "client_id": "client_alpha",
  "date_range": {
    "mode": "relative",
    "last_n_days": 7,
    "anchor_date": "2026-07-11"
  },
  "filters": {
    "campaign_ids": ["camp_104"]
  },
  "select_columns": [
    "date",
    "client_id",
    "campaign_id",
    "device",
    "impressions",
    "views",
    "clicks",
    "spend"
  ],
  "output": {
    "path": "outputs/client_alpha_device_last_7_days.csv"
  }
}
```

Run:

```bash
/usr/bin/python3 scripts/run_extraction.py --config configs/client_alpha_device_last_7_days.json
```

Sample output rows:

```csv
date,client_id,campaign_id,device,impressions,views,clicks,spend
2026-07-07,client_alpha,camp_104,MOBILE,11000,7200,480,240.00
2026-07-07,client_alpha,camp_104,DESKTOP,5000,3000,210,120.00
2026-07-07,client_alpha,camp_104,TV,4000,2300,100,60.40
```

## Where the logic lives

- CLI: `src/youtube_extractor/cli.py`
- Extractor flow: `src/youtube_extractor/extractors/youtube_ads_extractor.py`
- Filtering helpers: `src/youtube_extractor/helpers/filter_helpers.py`
- Date/CSV utils: `src/youtube_extractor/utils/`
