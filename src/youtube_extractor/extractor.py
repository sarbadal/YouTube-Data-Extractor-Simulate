"""Backward-compatible extractor import.

Use extractors.youtube_ads_extractor for new code.
"""

from youtube_extractor.extractors.youtube_ads_extractor import run_extraction

__all__ = ["run_extraction"]
