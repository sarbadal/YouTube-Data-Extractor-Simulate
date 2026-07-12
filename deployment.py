"""Deployment helper for Google Cloud Functions + GCS static assets.

This script does three jobs:
1. Upload local static assets to a GCS bucket under a versioned prefix.
2. Build production environment variables with STATIC_BASE_URL.
3. Deploy the Flask app to Google Cloud Functions using gcloud CLI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from google.api_core.exceptions import NotFound
from google.cloud import storage


PROJECT_ROOT = Path(__file__).resolve().parent


SUPPORTED_STATIC_SUFFIXES = {
	".js",
	".css",
	".png",
	".jpg",
	".jpeg",
	".gif",
	".svg",
	".webp",
	".ico",
	".json",
	".txt",
	".map",
	".woff",
	".woff2",
	".ttf",
	".eot",
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Deploy Flask app to Google Cloud Functions and publish static assets to GCS."
	)
	parser.add_argument("--project-id", required=True, help="GCP project id")
	parser.add_argument("--function-name", required=True, help="Cloud Function name")
	parser.add_argument("--region", default="us-central1", help="GCP region")
	parser.add_argument("--runtime", default="python311", help="Cloud Function runtime")
	parser.add_argument("--entry-point", default="entry_point", help="Function entry point")
	parser.add_argument(
		"--function-source",
		default="main.py",
		help="Function source file relative to --source (used for GOOGLE_FUNCTION_SOURCE).",
	)
	parser.add_argument(
		"--source",
		default=".",
		help="Path to function source. Must contain main.py (or the file with --entry-point).",
	)
	parser.add_argument("--bucket", required=True, help="GCS bucket for static files")
	parser.add_argument(
		"--bucket-location",
		default="US",
		help="Bucket location used only if bucket must be created",
	)
	parser.add_argument(
		"--static-dir",
		default="webapp/static",
		help="Local static directory to upload",
	)
	parser.add_argument(
		"--static-prefix",
		default="",
		help="Optional prefix inside bucket; if empty, uses static/<timestamp>",
	)
	parser.add_argument(
		"--url-prefix",
		default="",
		help="Optional base path where the app is mounted (e.g. /t-test).",
	)
	parser.add_argument(
		"--data-storage-mode",
		choices=("local", "gcs"),
		default="gcs",
		help="Where extraction templates/outputs are stored: local filesystem or GCS.",
	)
	parser.add_argument(
		"--data-bucket",
		default="",
		help="Bucket for extraction data/outputs when --data-storage-mode=gcs (defaults to --bucket).",
	)
	parser.add_argument(
		"--data-prefix",
		default="data",
		help="Input template folder prefix in data bucket when using GCS mode.",
	)
	parser.add_argument(
		"--output-prefix",
		default="outputs",
		help="Output folder prefix in data bucket when using GCS mode.",
	)
	parser.add_argument(
		"--service-account",
		default="",
		help="Optional service account email for function execution",
	)
	parser.add_argument(
		"--allow-unauthenticated",
		action="store_true",
		help="Allow unauthenticated function access",
	)
	parser.add_argument(
		"--env",
		action="append",
		default=[],
		metavar="KEY=VALUE",
		help="Additional environment variables (can be repeated)",
	)
	parser.add_argument(
		"--skip-upload",
		action="store_true",
		help="Skip static upload and keep existing STATIC_BASE_URL from --env",
	)
	parser.add_argument(
		"--write-env-file",
		default=".env.prod",
		help="Write computed production env vars to this file (set empty to disable)",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Print commands and resolved values without deploying",
	)
	return parser.parse_args()


def resolve_source_path(source_value: str) -> Path:
	source_path = Path(source_value)
	if not source_path.is_absolute():
		source_path = (PROJECT_ROOT / source_path).resolve()

	if not source_path.exists() or not source_path.is_dir():
		raise RuntimeError(f"Source directory not found: {source_path}")

	# Common pitfall: using --source src while entry point lives in project root main.py.
	if source_path.name == "src" and not (source_path / "main.py").exists():
		root_main = source_path.parent / "main.py"
		if root_main.exists():
			print(
				"Detected --source pointing to src/ without main.py. "
				"Using project root source so main.py can import the src package."
			)
			return source_path.parent

	return source_path


def resolve_static_dir(static_dir_value: str, source_path: Path) -> Path:
	static_dir = Path(static_dir_value)
	if static_dir.is_absolute():
		resolved = static_dir
	else:
		candidates = [
			(PROJECT_ROOT / static_dir).resolve(),
			(source_path / static_dir).resolve(),
		]
		resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

	if not resolved.exists() or not resolved.is_dir():
		raise RuntimeError(
			f"Static directory not found: {resolved} (from --static-dir {static_dir_value})"
		)

	return resolved


def validate_function_source(source_path: Path, function_source: str) -> str:
	function_source_path = Path(function_source)
	if function_source_path.is_absolute():
		raise RuntimeError("--function-source must be relative to --source, not an absolute path.")

	resolved = (source_path / function_source_path).resolve()
	try:
		resolved.relative_to(source_path)
	except ValueError as exc:
		raise RuntimeError("--function-source must remain inside --source directory.") from exc

	if not resolved.exists() or not resolved.is_file():
		raise RuntimeError(
			f"Function source file not found: {resolved}. "
			"Ensure it exists and is not excluded by .gcloudignore."
		)

	return function_source_path.as_posix()


def run_cmd(cmd: List[str], dry_run: bool = False) -> None:
	pretty = " ".join(cmd)
	print(f"\n$ {pretty}")
	if dry_run:
		return
	subprocess.run(cmd, check=True)


def require_gcloud() -> None:
	try:
		subprocess.run(["gcloud", "--version"], check=True, stdout=subprocess.DEVNULL)
	except (subprocess.CalledProcessError, FileNotFoundError) as exc:
		raise RuntimeError("gcloud CLI is required but was not found in PATH.") from exc


def parse_env_pairs(pairs: Iterable[str]) -> Dict[str, str]:
	env: Dict[str, str] = {}
	for item in pairs:
		if "=" not in item:
			raise ValueError(f"Invalid env var '{item}'. Expected KEY=VALUE format.")
		key, value = item.split("=", 1)
		key = key.strip()
		if not key:
			raise ValueError(f"Invalid env var '{item}'. Empty key.")
		env[key] = value
	return env


def ensure_bucket(client: storage.Client, bucket_name: str, location: str, project_id: str) -> storage.Bucket:
	bucket = client.bucket(bucket_name)
	try:
		client.get_bucket(bucket_name)
		print(f"Bucket exists: {bucket_name}")
		return bucket
	except NotFound:
		print(f"Bucket not found. Creating: {bucket_name} in {location}")
		bucket = client.create_bucket(bucket_or_name=bucket_name, location=location, project=project_id)
		return bucket


def iter_static_files(static_dir: Path) -> Iterable[Tuple[Path, str]]:
	for path in static_dir.rglob("*"):
		if not path.is_file():
			continue
		if path.suffix.lower() not in SUPPORTED_STATIC_SUFFIXES:
			continue
		rel = path.relative_to(static_dir).as_posix()
		yield path, rel


def upload_static_assets(
	client: storage.Client,
	bucket_name: str,
	static_dir: Path,
	static_prefix: str,
	cache_control: str = "public, max-age=31536000, immutable",
) -> str:
	bucket = client.bucket(bucket_name)
	uploaded = 0
	for local_path, rel in iter_static_files(static_dir):
		object_name = f"{static_prefix}/{rel}" if static_prefix else rel
		object_name = object_name.lstrip("/")
		blob = bucket.blob(object_name)
		content_type, _ = mimetypes.guess_type(local_path.name)
		if not content_type:
			content_type = "application/octet-stream"
		blob.cache_control = cache_control
		blob.upload_from_filename(str(local_path), content_type=content_type)
		uploaded += 1
	if uploaded == 0:
		raise RuntimeError(f"No static files found to upload in: {static_dir}")
	print(f"Uploaded {uploaded} static file(s) to gs://{bucket_name}/{static_prefix}")
	return f"https://storage.googleapis.com/{bucket_name}/{static_prefix}".rstrip("/")


def ensure_public_object_access(bucket_name: str, dry_run: bool = False) -> None:
	"""Grant public read access to bucket objects for static hosting."""
	run_cmd(
		[
			"gcloud",
			"storage",
			"buckets",
			"add-iam-policy-binding",
			f"gs://{bucket_name}",
			"--member=allUsers",
			"--role=roles/storage.objectViewer",
		],
		dry_run=dry_run,
	)


def build_deploy_command(args: argparse.Namespace, env_vars: Dict[str, str]) -> List[str]:
	cmd = [
		"gcloud",
		"functions",
		"deploy",
		args.function_name,
		"--gen2",
		"--region",
		args.region,
		"--runtime",
		args.runtime,
		"--trigger-http",
		"--entry-point",
		args.entry_point,
		"--source",
		args.source,
		"--project",
		args.project_id,
	]

	if args.allow_unauthenticated:
		cmd.append("--allow-unauthenticated")

	if args.service_account:
		cmd.extend(["--service-account", args.service_account])

	if env_vars:
		env_str = ",".join(f"{key}={value}" for key, value in sorted(env_vars.items()))
		cmd.extend(["--set-env-vars", env_str])

	cmd.extend(["--set-build-env-vars", f"GOOGLE_FUNCTION_SOURCE={args.function_source}"])

	return cmd


def maybe_write_env_file(path_value: str, env_vars: Dict[str, str]) -> None:
	if not path_value:
		return
	path = Path(path_value)
	lines = [f"{k}={v}" for k, v in sorted(env_vars.items())]
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")
	print(f"Wrote production env file: {path}")


def main() -> int:
	args = parse_args()

	require_gcloud()

	source_path = resolve_source_path(args.source)
	args.source = str(source_path)
	args.function_source = validate_function_source(source_path, args.function_source)

	env_vars = parse_env_pairs(args.env)
	env_vars.setdefault("ENV_TYPE", "prod")
	env_vars.setdefault("FLASK_DEBUG", "0")
	env_vars.setdefault("DATA_STORAGE_MODE", args.data_storage_mode)

	if args.data_storage_mode == "gcs":
		data_bucket = args.data_bucket.strip() or args.bucket
		env_vars.setdefault("GCS_DATA_BUCKET", data_bucket)
		env_vars.setdefault("GCS_DATA_PREFIX", args.data_prefix.strip().strip("/") or "data")
		env_vars.setdefault("GCS_OUTPUT_PREFIX", args.output_prefix.strip().strip("/") or "outputs")

	if args.url_prefix:
		env_vars["URL_PREFIX"] = args.url_prefix

	if not args.skip_upload:
		static_dir = resolve_static_dir(args.static_dir, source_path)

		timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
		static_prefix = args.static_prefix.strip("/") or f"static/{timestamp}"

		client = storage.Client(project=args.project_id)
		ensure_bucket(
			client=client,
			bucket_name=args.bucket,
			location=args.bucket_location,
			project_id=args.project_id,
		)
		ensure_public_object_access(args.bucket, dry_run=args.dry_run)
		static_base_url = upload_static_assets(
			client=client,
			bucket_name=args.bucket,
			static_dir=static_dir,
			static_prefix=static_prefix,
		)
		env_vars["STATIC_BASE_URL"] = static_base_url

	if "STATIC_BASE_URL" not in env_vars:
		raise RuntimeError(
			"STATIC_BASE_URL is missing. Either upload static files or provide it via --env STATIC_BASE_URL=..."
		)

	print("\nResolved production environment variables:")
	for key, value in sorted(env_vars.items()):
		print(f"- {key}={value}")

	maybe_write_env_file(args.write_env_file, env_vars)
	deploy_cmd = build_deploy_command(args, env_vars)
	run_cmd(deploy_cmd, dry_run=args.dry_run)
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:  # pylint: disable=broad-except
		print(f"Deployment failed: {exc}", file=sys.stderr)
		raise SystemExit(1)