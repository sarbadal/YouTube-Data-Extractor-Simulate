"""Backward-compatible config imports.

Use models.config_models for new code.
"""

from youtube_extractor.models.config_models import ExtractionConfig, load_config

__all__ = ["ExtractionConfig", "load_config"]
