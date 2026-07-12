from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from .constants import CONFIG_OUTPUT_DIR, PROJECT_ROOT, SRC_PATH

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from youtube_extractor.extractors import run_extraction
from youtube_extractor.extractors.youtube_ads_extractor import DATASET_TO_FILE
from youtube_extractor.models import load_config

REPORT_RETENTION_LIMIT = 5


def _is_gcs_data_mode() -> bool:
    mode = os.getenv("DATA_STORAGE_MODE", "local").strip().lower()
    env_type = os.getenv("ENV_TYPE", "dev").strip().lower()
    bucket_name = os.getenv("GCS_DATA_BUCKET", "").strip()

    if mode == "gcs":
        if not bucket_name:
            raise RuntimeError("GCS_DATA_BUCKET must be set when DATA_STORAGE_MODE=gcs")
        return True

    if bucket_name:
        return True

    if env_type == "prod":
        raise RuntimeError(
            "Production requires GCS-backed storage. Set DATA_STORAGE_MODE=gcs and GCS_DATA_BUCKET."
        )

    return False


def _get_gcs_client():
    try:
        from google.cloud import storage
    except ImportError as exc:  # pragma: no cover - import guard for local-only runs
        raise RuntimeError("google-cloud-storage is required when DATA_STORAGE_MODE=gcs") from exc
    return storage.Client()


def _get_gcs_bucket_name() -> str:
    bucket_name = os.getenv("GCS_DATA_BUCKET", "").strip()
    if not bucket_name:
        raise RuntimeError("GCS_DATA_BUCKET must be set when DATA_STORAGE_MODE=gcs")
    return bucket_name


def _get_gcs_output_prefix() -> str:
    return os.getenv("GCS_OUTPUT_PREFIX", "outputs").strip().strip("/")


def _build_public_gcs_url(bucket_name: str, blob_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name.lstrip('/')}"


def _build_output_blob_name(file_name: str) -> str:
    output_prefix = _get_gcs_output_prefix()
    return f"{output_prefix}/{file_name}".strip("/")


def upload_local_file_to_gcs(local_path: Path, bucket_name: str, blob_name: str, content_type: str) -> str:
    """Upload a local file to GCS and return a public URL."""
    if not local_path.exists() or not local_path.is_file():
        raise FileNotFoundError(f"Local file does not exist: {local_path}")

    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type=content_type)
    return _build_public_gcs_url(bucket_name, blob_name)


def download_gcs_file_to_local(bucket_name: str, blob_name: str, local_path: Path) -> Path:
    """Download a GCS object to local filesystem and return the local path."""
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not blob.exists(client=client):
        raise FileNotFoundError(f"GCS object does not exist: gs://{bucket_name}/{blob_name}")

    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_path))
    return local_path


def save_generated_config(config_payload: dict) -> Path:
    CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config_name = f"config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    config_path = CONFIG_OUTPUT_DIR / config_name
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return config_path


def ensure_required_dataset_local(config_path: Path) -> None:
    """Download only the required dataset template from GCS into local data/ for extraction."""
    if not _is_gcs_data_mode():
        return

    config = load_config(config_path)
    dataset_file = DATASET_TO_FILE.get(config.dataset)
    if not dataset_file:
        raise ValueError(f"Unsupported dataset: {config.dataset}")

    bucket_name = _get_gcs_bucket_name()
    data_prefix = os.getenv("GCS_DATA_PREFIX", "data").strip().strip("/")
    blob_name = f"{data_prefix}/{dataset_file}".strip("/")
    local_data_path = PROJECT_ROOT / "data" / dataset_file

    download_gcs_file_to_local(
        bucket_name=bucket_name,
        blob_name=blob_name,
        local_path=local_data_path,
    )


def execute_extraction(config_path: Path) -> tuple[Path, str]:
    ensure_required_dataset_local(config_path)
    output_path = run_extraction(config_path=config_path, project_root=PROJECT_ROOT)
    output_ref = output_path.relative_to(PROJECT_ROOT)

    if _is_gcs_data_mode():
        bucket_name = _get_gcs_bucket_name()
        blob_name = _build_output_blob_name(output_path.name)
        public_url = upload_local_file_to_gcs(
            local_path=output_path,
            bucket_name=bucket_name,
            blob_name=blob_name,
            content_type="text/csv",
        )

        # Keep container filesystem clean in GCS mode after upload.
        try:
            output_path.unlink()
        except OSError:
            pass

        return Path(blob_name), public_url

    return output_ref, ""


def resolve_output_download_payload(file_param: str) -> tuple[Path | BinaryIO, str]:
    if _is_gcs_data_mode():
        normalized = file_param.strip().lstrip("/")
        output_prefix = _get_gcs_output_prefix()
        required_prefix = f"{output_prefix}/"
        if not normalized.startswith(required_prefix):
            raise ValueError("Invalid download path")

        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blob = bucket.blob(normalized)
        if not blob.exists(client=client):
            raise FileNotFoundError("Requested file does not exist")

        payload = io.BytesIO(blob.download_as_bytes())
        payload.seek(0)
        return payload, Path(normalized).name

    target = (PROJECT_ROOT / file_param).resolve()
    outputs_root = (PROJECT_ROOT / "outputs").resolve()

    if not str(target).startswith(str(outputs_root)):
        raise ValueError("Invalid download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested file does not exist")

    return target, target.name


def resolve_config_download_path(file_param: str) -> Path:
    target = (PROJECT_ROOT / file_param).resolve()
    configs_root = CONFIG_OUTPUT_DIR.resolve()

    if not str(target).startswith(str(configs_root)):
        raise ValueError("Invalid config download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested config file does not exist")

    return target


def list_reports_for_client(client_id: str) -> list[str]:
    if _is_gcs_data_mode():
        output_prefix = _get_gcs_output_prefix()
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blobs = sorted(
            bucket.list_blobs(prefix=f"{output_prefix}/report_{client_id}_"),
            key=lambda blob: blob.updated or datetime.min,
            reverse=True,
        )
        return [blob.name for blob in blobs if blob.name.endswith(".csv")]

    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    matches = sorted(
        outputs_root.glob(f"report_{client_id}_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [path.relative_to(PROJECT_ROOT).as_posix() for path in matches]


def list_all_reports() -> list[str]:
    if _is_gcs_data_mode():
        output_prefix = _get_gcs_output_prefix()
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blobs = sorted(
            bucket.list_blobs(prefix=f"{output_prefix}/report_"),
            key=lambda blob: blob.updated or datetime.min,
            reverse=True,
        )
        return [blob.name for blob in blobs if blob.name.endswith(".csv")]

    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    return [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in sorted(
            outputs_root.glob("report_*.csv"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    ]


def prune_old_reports(max_reports: int = REPORT_RETENTION_LIMIT) -> int:
    """Delete older generated report CSV files and keep only the newest max_reports.

    Returns the number of deleted files.
    """
    if max_reports < 1:
        return 0

    reports = list_all_reports()
    stale_reports = reports[max_reports:]

    if _is_gcs_data_mode():
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        deleted = 0
        for blob_name in stale_reports:
            try:
                bucket.blob(blob_name).delete()
                deleted += 1
            except Exception:  # noqa: BLE001
                continue
        return deleted

    deleted = 0
    for report_ref in stale_reports:
        try:
            (PROJECT_ROOT / report_ref).unlink()
            deleted += 1
        except OSError:
            # Ignore file deletion failures so report generation flow does not fail.
            continue

    return deleted


def list_recent_report_config_pairs(limit: int = 20) -> list[dict[str, str]]:
    recent_reports = list_all_reports()[:limit]
    pairs: list[dict[str, str]] = []
    report_bucket = _get_gcs_bucket_name() if _is_gcs_data_mode() else ""

    for report_ref in recent_reports:
        report_name = Path(report_ref).name
        timestamp_match = re.search(r"_(\d{8}_\d{6})\.csv$", report_name)
        config_rel = ""

        if timestamp_match:
            timestamp_token = timestamp_match.group(1)
            config_matches = sorted(
                CONFIG_OUTPUT_DIR.glob(f"config_{timestamp_token}_*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if config_matches:
                config_rel = config_matches[0].relative_to(PROJECT_ROOT).as_posix()

        pairs.append(
            {
                "report_file": report_ref,
                "report_name": report_name,
                "report_public_url": _build_public_gcs_url(report_bucket, report_ref)
                if report_bucket
                else "",
                "config_file": config_rel,
                "config_name": Path(config_rel).name if config_rel else "",
            }
        )

    return pairs
