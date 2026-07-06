"""Evaluation runners for different scenarios."""

from cobweaverclaw_compress.evals.runners.before_after import BeforeAfterRunner
from cobweaverclaw_compress.evals.runners.compression_only import CompressionOnlyRunner

__all__ = ["BeforeAfterRunner", "CompressionOnlyRunner"]
