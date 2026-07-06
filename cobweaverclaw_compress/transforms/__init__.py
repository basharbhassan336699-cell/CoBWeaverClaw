"""Transform modules for CoBWeaverClaw SDK."""

from __future__ import annotations

import importlib.util
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Expose concrete types to static analysis while keeping runtime imports lazy.
    from cobweaverclaw_compress.transforms.anchor_selector import (  # noqa: F401
        AnchorSelector,
        AnchorStrategy,
        AnchorWeights,
        DataPattern,
        calculate_information_score,
        compute_item_hash,
    )
    from cobweaverclaw_compress.transforms.base import Transform  # noqa: F401
    from cobweaverclaw_compress.transforms.cache_aligner import CacheAligner  # noqa: F401
    from cobweaverclaw_compress.transforms.code_compressor import (  # noqa: F401
        CodeAwareCompressor,
        CodeCompressionResult,
        CodeCompressorConfig,
        CodeLanguage,
        DocstringMode,
        detect_language,
        is_tree_sitter_available,
    )
    from cobweaverclaw_compress.transforms.content_detector import (  # noqa: F401
        ContentType,
        DetectionResult,
        detect_content_type,
    )
    from cobweaverclaw_compress.transforms.content_router import (  # noqa: F401
        CompressionStrategy,
        ContentRouter,
        ContentRouterConfig,
        RouterCompressionResult,
    )
    from cobweaverclaw_compress.transforms.diff_compressor import (  # noqa: F401
        DiffCompressionResult,
        DiffCompressor,
        DiffCompressorConfig,
    )
    from cobweaverclaw_compress.transforms.html_extractor import (  # noqa: F401
        HTMLExtractionResult,
        HTMLExtractor,
        HTMLExtractorConfig,
        is_html_content,
    )
    from cobweaverclaw_compress.transforms.log_compressor import (  # noqa: F401
        LogCompressionResult,
        LogCompressor,
        LogCompressorConfig,
    )
    from cobweaverclaw_compress.transforms.pipeline import TransformPipeline  # noqa: F401
    from cobweaverclaw_compress.transforms.search_compressor import (  # noqa: F401
        SearchCompressionResult,
        SearchCompressor,
        SearchCompressorConfig,
    )
    from cobweaverclaw_compress.transforms.smart_crusher import SmartCrusher, SmartCrusherConfig  # noqa: F401
    from cobweaverclaw_compress.transforms.tabular_ingest import (  # noqa: F401
        TabularCompressionResult,
        TabularCompressor,
        TabularCompressorConfig,
    )

_HTML_EXTRACTOR_AVAILABLE = importlib.util.find_spec("trafilatura") is not None

__all__ = [
    # Base
    "Transform",
    "TransformPipeline",
    # Anchor selection
    "AnchorSelector",
    "AnchorStrategy",
    "AnchorWeights",
    "DataPattern",
    "calculate_information_score",
    "compute_item_hash",
    # JSON compression
    "SmartCrusher",
    "SmartCrusherConfig",
    # Text compression (coding tasks)
    "ContentType",
    "DetectionResult",
    "detect_content_type",
    "SearchCompressor",
    "SearchCompressorConfig",
    "SearchCompressionResult",
    "LogCompressor",
    "LogCompressorConfig",
    "LogCompressionResult",
    "TabularCompressor",
    "TabularCompressorConfig",
    "TabularCompressionResult",
    "DiffCompressor",
    "DiffCompressorConfig",
    "DiffCompressionResult",
    # Code-aware compression (AST-based)
    "CodeAwareCompressor",
    "CodeCompressorConfig",
    "CodeCompressionResult",
    "CodeLanguage",
    "DocstringMode",
    "detect_language",
    "is_tree_sitter_available",
    # Content routing
    "ContentRouter",
    "ContentRouterConfig",
    "RouterCompressionResult",
    "CompressionStrategy",
    # Other transforms
    "CacheAligner",
    # HTML extraction (optional)
    "_HTML_EXTRACTOR_AVAILABLE",
]

# Conditionally add HTML extractor exports
if _HTML_EXTRACTOR_AVAILABLE:
    __all__.extend(
        [
            "HTMLExtractor",
            "HTMLExtractorConfig",
            "HTMLExtractionResult",
            "is_html_content",
        ]
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Base
    "Transform": ("cobweaverclaw_compress.transforms.base", "Transform"),
    "TransformPipeline": ("cobweaverclaw_compress.transforms.pipeline", "TransformPipeline"),
    # Anchor selection
    "AnchorSelector": ("cobweaverclaw_compress.transforms.anchor_selector", "AnchorSelector"),
    "AnchorStrategy": ("cobweaverclaw_compress.transforms.anchor_selector", "AnchorStrategy"),
    "AnchorWeights": ("cobweaverclaw_compress.transforms.anchor_selector", "AnchorWeights"),
    "DataPattern": ("cobweaverclaw_compress.transforms.anchor_selector", "DataPattern"),
    "calculate_information_score": (
        "cobweaverclaw_compress.transforms.anchor_selector",
        "calculate_information_score",
    ),
    "compute_item_hash": ("cobweaverclaw_compress.transforms.anchor_selector", "compute_item_hash"),
    # JSON compression
    "SmartCrusher": ("cobweaverclaw_compress.transforms.smart_crusher", "SmartCrusher"),
    "SmartCrusherConfig": ("cobweaverclaw_compress.transforms.smart_crusher", "SmartCrusherConfig"),
    # Text compression (coding tasks)
    "ContentType": ("cobweaverclaw_compress.transforms.content_detector", "ContentType"),
    "DetectionResult": ("cobweaverclaw_compress.transforms.content_detector", "DetectionResult"),
    "detect_content_type": ("cobweaverclaw_compress.transforms.content_detector", "detect_content_type"),
    "SearchCompressor": ("cobweaverclaw_compress.transforms.search_compressor", "SearchCompressor"),
    "SearchCompressorConfig": (
        "cobweaverclaw_compress.transforms.search_compressor",
        "SearchCompressorConfig",
    ),
    "SearchCompressionResult": (
        "cobweaverclaw_compress.transforms.search_compressor",
        "SearchCompressionResult",
    ),
    "LogCompressor": ("cobweaverclaw_compress.transforms.log_compressor", "LogCompressor"),
    "LogCompressorConfig": ("cobweaverclaw_compress.transforms.log_compressor", "LogCompressorConfig"),
    "LogCompressionResult": ("cobweaverclaw_compress.transforms.log_compressor", "LogCompressionResult"),
    "TabularCompressor": ("cobweaverclaw_compress.transforms.tabular_ingest", "TabularCompressor"),
    "TabularCompressorConfig": (
        "cobweaverclaw_compress.transforms.tabular_ingest",
        "TabularCompressorConfig",
    ),
    "TabularCompressionResult": (
        "cobweaverclaw_compress.transforms.tabular_ingest",
        "TabularCompressionResult",
    ),
    "DiffCompressor": ("cobweaverclaw_compress.transforms.diff_compressor", "DiffCompressor"),
    "DiffCompressorConfig": ("cobweaverclaw_compress.transforms.diff_compressor", "DiffCompressorConfig"),
    "DiffCompressionResult": (
        "cobweaverclaw_compress.transforms.diff_compressor",
        "DiffCompressionResult",
    ),
    # Code-aware compression (AST-based)
    "CodeAwareCompressor": ("cobweaverclaw_compress.transforms.code_compressor", "CodeAwareCompressor"),
    "CodeCompressorConfig": ("cobweaverclaw_compress.transforms.code_compressor", "CodeCompressorConfig"),
    "CodeCompressionResult": (
        "cobweaverclaw_compress.transforms.code_compressor",
        "CodeCompressionResult",
    ),
    "CodeLanguage": ("cobweaverclaw_compress.transforms.code_compressor", "CodeLanguage"),
    "DocstringMode": ("cobweaverclaw_compress.transforms.code_compressor", "DocstringMode"),
    "detect_language": ("cobweaverclaw_compress.transforms.code_compressor", "detect_language"),
    "is_tree_sitter_available": (
        "cobweaverclaw_compress.transforms.code_compressor",
        "is_tree_sitter_available",
    ),
    # Content routing
    "ContentRouter": ("cobweaverclaw_compress.transforms.content_router", "ContentRouter"),
    "ContentRouterConfig": ("cobweaverclaw_compress.transforms.content_router", "ContentRouterConfig"),
    "RouterCompressionResult": (
        "cobweaverclaw_compress.transforms.content_router",
        "RouterCompressionResult",
    ),
    "CompressionStrategy": ("cobweaverclaw_compress.transforms.content_router", "CompressionStrategy"),
    # Other transforms
    "CacheAligner": ("cobweaverclaw_compress.transforms.cache_aligner", "CacheAligner"),
    # HTML extraction (optional dependency - requires trafilatura)
    "HTMLExtractor": ("cobweaverclaw_compress.transforms.html_extractor", "HTMLExtractor"),
    "HTMLExtractorConfig": ("cobweaverclaw_compress.transforms.html_extractor", "HTMLExtractorConfig"),
    "HTMLExtractionResult": ("cobweaverclaw_compress.transforms.html_extractor", "HTMLExtractionResult"),
    "is_html_content": ("cobweaverclaw_compress.transforms.html_extractor", "is_html_content"),
}


def __getattr__(name: str) -> object:
    if name == "__path__":
        raise AttributeError(name)
    if name == "_HTML_EXTRACTOR_AVAILABLE":
        return _HTML_EXTRACTOR_AVAILABLE

    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
