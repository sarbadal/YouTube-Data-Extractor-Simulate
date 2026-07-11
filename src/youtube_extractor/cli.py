from __future__ import annotations

import argparse
from pathlib import Path

from .extractors import run_extraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube campaign extraction simulator")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_path = run_extraction(Path(args.config))
    print(f"Extraction complete. Output: {output_path}")


if __name__ == "__main__":
    main()
