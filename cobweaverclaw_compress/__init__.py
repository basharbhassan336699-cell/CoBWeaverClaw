"""
CoBWeaverClaw - The Context Optimization Layer for LLM Applications.

Cut your LLM costs by 50-90% without losing accuracy.

CoBWeaverClaw wraps LLM clients to provide:
- Smart compression of tool outputs (keeps errors, anomalies, relevant items)
- Cache-aligned prefix optimization for better provider cache hits
- Rolling window token management for long conversations
- Full streaming support with zero accuracy loss

Quick Start:

    from cobweaverclaw_compress import CoBWeaverClawClient, OpenAIProvider
    from openai import OpenAI

    # Wrap your existing client
    client = CoBWeaverClawClient(
        original_client=OpenAI(),
        provider=OpenAIProvider(),
        default_mode="optimize",
    )

    # Use exactly like the original client
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello!"},
        ],
    )

    # Check savings
    stats = client.get_stats()
    print(f"Tokens saved: {stats['session']['tokens_saved_total']}")

Verify It's Working:

    # Validate configuration
    result = client.validate_setup()
    if not result["valid"]:
        print("Issues:", result)

    # Enable logging to see what's happening
    import logging
    logging.basicConfig(level=logging.INFO)
    # INFO:cobweaverclaw_compress.transforms.pipeline:Pipeline complete: 45000 -> 4500 tokens

Simulate Before Sending:

    plan = client.chat.completions.simulate(
        model="gpt-4o",
        messages=large_messages,
    )
    print(f"Would save {plan.tokens_saved} tokens")
    print(f"Transforms: {plan.transforms}")

Error Handling:

    from cobweaverclaw_compress import CoBWeaverClawError, ConfigurationError, ProviderError

    try:
        response = client.chat.completions.create(...)
    except ConfigurationError as e:
        print(f"Config issue: {e.details}")
    except CoBWeaverClawError as e:
        print(f"CoBWeaverClaw error: {e}")

For more examples, see https://github.com/cobweaverclaw_compress-sdk/cobweaverclaw_compress/tree/main/examples
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from ._ort import ensure_ort_dylib_pinned
from ._version import __version__  # noqa: F401

# Must run before anything can import `cobweaverclaw_compress._core`: on Windows the
# Rust core resolves onnxruntime.dll at runtime (ort load-dynamic), and
# the bare DLL search lands on the Windows ML System32 build, which
# deadlocks ort session init (Win11 24H2+). Windows-gated, idempotent,
# ~microseconds. See `cobweaverclaw_compress/_ort.py` for the full story.
ensure_ort_dylib_pinned()

from .compress import CompressConfig, CompressResult, compress, compress_spreadsheet  # noqa: E402

# Keep a real callable bound for the one-function compression API so
# `from cobweaverclaw_compress import compress` is never shadowed by the submodule object.

__all__ = [
    # Main client
    "CoBWeaverClawClient",
    # Providers
    "Provider",
    "TokenCounter",
    "OpenAIProvider",
    "AnthropicProvider",
    # Exceptions
    "CoBWeaverClawError",
    "ConfigurationError",
    "ProviderError",
    "StorageError",
    "CompressionError",
    "TokenizationError",
    "CacheError",
    "ValidationError",
    "TransformError",
    # Config
    "CoBWeaverClawConfig",
    "CoBWeaverClawMode",
    "SmartCrusherConfig",
    "CacheAlignerConfig",
    "CacheOptimizerConfig",
    "RelevanceScorerConfig",
    # Data models
    "Block",
    "CachePrefixMetrics",
    "DiffArtifact",
    "RequestMetrics",
    "SimulationResult",
    "TransformDiff",
    "TransformResult",
    "WasteSignals",
    # Transforms
    "SmartCrusher",
    "CacheAligner",
    "TransformPipeline",
    # Cache optimizers
    "BaseCacheOptimizer",
    "CacheConfig",
    "CacheMetrics",
    "CacheResult",
    "CacheStrategy",
    "OptimizationContext",
    "CacheOptimizerRegistry",
    "AnthropicCacheOptimizer",
    "OpenAICacheOptimizer",
    "GoogleCacheOptimizer",
    "SemanticCache",
    "SemanticCacheLayer",
    # Relevance scoring - BM25 always available, embeddings require sentence-transformers
    "RelevanceScore",
    "RelevanceScorer",
    "BM25Scorer",
    "EmbeddingScorer",
    "HybridScorer",
    "create_scorer",
    "embedding_available",
    # Utilities
    "Tokenizer",
    "count_tokens_text",
    "count_tokens_messages",
    "generate_report",
    # Observability
    "CoBWeaverClawOtelMetrics",
    "CoBWeaverClawTracer",
    "LangfuseTracingConfig",
    "OTelMetricsConfig",
    "configure_otel_metrics",
    "configure_langfuse_tracing",
    "get_cobweaverclaw_compress_tracer",
    "get_langfuse_tracing_status",
    "get_otel_metrics",
    "get_otel_metrics_status",
    "reset_cobweaverclaw_compress_tracing",
    "reset_otel_metrics",
    # Memory - optional hierarchical memory system
    "with_memory",  # Main user-facing API
    "Memory",
    "ScopeLevel",
    "HierarchicalMemory",
    "MemoryConfig",
    "EmbedderBackend",
    # One-function compression API
    "compress",
    "compress_spreadsheet",
    "CompressConfig",
    "CompressResult",
    # Hooks
    "CompressionHooks",
    "CompressContext",
    "CompressEvent",
    # Canonical pipeline
    "PipelineStage",
    "PipelineEvent",
    "PipelineExtensionManager",
    "CANONICAL_PIPELINE_STAGES",
    # Shared context for multi-agent workflows
    "SharedContext",
]

# Keep package-level imports lightweight so `import cobweaverclaw_compress` does not eagerly
# load provider SDKs, ML stacks, or optional proxy/runtime integrations.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Main client
    "CoBWeaverClawClient": ("cobweaverclaw_compress.client", "CoBWeaverClawClient"),
    # Providers
    "Provider": ("cobweaverclaw_compress.providers", "Provider"),
    "TokenCounter": ("cobweaverclaw_compress.providers", "TokenCounter"),
    "OpenAIProvider": ("cobweaverclaw_compress.providers", "OpenAIProvider"),
    "AnthropicProvider": ("cobweaverclaw_compress.providers", "AnthropicProvider"),
    # Exceptions
    "CoBWeaverClawError": ("cobweaverclaw_compress.exceptions", "CoBWeaverClawError"),
    "ConfigurationError": ("cobweaverclaw_compress.exceptions", "ConfigurationError"),
    "ProviderError": ("cobweaverclaw_compress.exceptions", "ProviderError"),
    "StorageError": ("cobweaverclaw_compress.exceptions", "StorageError"),
    "CompressionError": ("cobweaverclaw_compress.exceptions", "CompressionError"),
    "TokenizationError": ("cobweaverclaw_compress.exceptions", "TokenizationError"),
    "CacheError": ("cobweaverclaw_compress.exceptions", "CacheError"),
    "ValidationError": ("cobweaverclaw_compress.exceptions", "ValidationError"),
    "TransformError": ("cobweaverclaw_compress.exceptions", "TransformError"),
    # Config
    "CoBWeaverClawConfig": ("cobweaverclaw_compress.config", "CoBWeaverClawConfig"),
    "CoBWeaverClawMode": ("cobweaverclaw_compress.config", "CoBWeaverClawMode"),
    "SmartCrusherConfig": ("cobweaverclaw_compress.config", "SmartCrusherConfig"),
    "CacheAlignerConfig": ("cobweaverclaw_compress.config", "CacheAlignerConfig"),
    "CacheOptimizerConfig": ("cobweaverclaw_compress.config", "CacheOptimizerConfig"),
    "RelevanceScorerConfig": ("cobweaverclaw_compress.config", "RelevanceScorerConfig"),
    # Data models
    "Block": ("cobweaverclaw_compress.config", "Block"),
    "CachePrefixMetrics": ("cobweaverclaw_compress.config", "CachePrefixMetrics"),
    "DiffArtifact": ("cobweaverclaw_compress.config", "DiffArtifact"),
    "RequestMetrics": ("cobweaverclaw_compress.config", "RequestMetrics"),
    "SimulationResult": ("cobweaverclaw_compress.config", "SimulationResult"),
    "TransformDiff": ("cobweaverclaw_compress.config", "TransformDiff"),
    "TransformResult": ("cobweaverclaw_compress.config", "TransformResult"),
    "WasteSignals": ("cobweaverclaw_compress.config", "WasteSignals"),
    # Transforms
    "SmartCrusher": ("cobweaverclaw_compress.transforms", "SmartCrusher"),
    "CacheAligner": ("cobweaverclaw_compress.transforms", "CacheAligner"),
    "TransformPipeline": ("cobweaverclaw_compress.transforms", "TransformPipeline"),
    # Cache optimizers
    "BaseCacheOptimizer": ("cobweaverclaw_compress.cache", "BaseCacheOptimizer"),
    "CacheConfig": ("cobweaverclaw_compress.cache", "CacheConfig"),
    "CacheMetrics": ("cobweaverclaw_compress.cache", "CacheMetrics"),
    "CacheResult": ("cobweaverclaw_compress.cache", "CacheResult"),
    "CacheStrategy": ("cobweaverclaw_compress.cache", "CacheStrategy"),
    "OptimizationContext": ("cobweaverclaw_compress.cache", "OptimizationContext"),
    "CacheOptimizerRegistry": ("cobweaverclaw_compress.cache", "CacheOptimizerRegistry"),
    "AnthropicCacheOptimizer": ("cobweaverclaw_compress.cache", "AnthropicCacheOptimizer"),
    "OpenAICacheOptimizer": ("cobweaverclaw_compress.cache", "OpenAICacheOptimizer"),
    "GoogleCacheOptimizer": ("cobweaverclaw_compress.cache", "GoogleCacheOptimizer"),
    "SemanticCache": ("cobweaverclaw_compress.cache", "SemanticCache"),
    "SemanticCacheLayer": ("cobweaverclaw_compress.cache", "SemanticCacheLayer"),
    # Relevance scoring
    "RelevanceScore": ("cobweaverclaw_compress.relevance", "RelevanceScore"),
    "RelevanceScorer": ("cobweaverclaw_compress.relevance", "RelevanceScorer"),
    "BM25Scorer": ("cobweaverclaw_compress.relevance", "BM25Scorer"),
    "EmbeddingScorer": ("cobweaverclaw_compress.relevance", "EmbeddingScorer"),
    "HybridScorer": ("cobweaverclaw_compress.relevance", "HybridScorer"),
    "create_scorer": ("cobweaverclaw_compress.relevance", "create_scorer"),
    "embedding_available": ("cobweaverclaw_compress.relevance", "embedding_available"),
    # Utilities
    "Tokenizer": ("cobweaverclaw_compress.tokenizer", "Tokenizer"),
    "count_tokens_text": ("cobweaverclaw_compress.tokenizer", "count_tokens_text"),
    "count_tokens_messages": ("cobweaverclaw_compress.tokenizer", "count_tokens_messages"),
    "generate_report": ("cobweaverclaw_compress.reporting", "generate_report"),
    # Observability
    "CoBWeaverClawOtelMetrics": ("cobweaverclaw_compress.observability", "CoBWeaverClawOtelMetrics"),
    "CoBWeaverClawTracer": ("cobweaverclaw_compress.observability", "CoBWeaverClawTracer"),
    "LangfuseTracingConfig": ("cobweaverclaw_compress.observability", "LangfuseTracingConfig"),
    "OTelMetricsConfig": ("cobweaverclaw_compress.observability", "OTelMetricsConfig"),
    "configure_otel_metrics": ("cobweaverclaw_compress.observability", "configure_otel_metrics"),
    "configure_langfuse_tracing": ("cobweaverclaw_compress.observability", "configure_langfuse_tracing"),
    "get_cobweaverclaw_compress_tracer": ("cobweaverclaw_compress.observability", "get_cobweaverclaw_compress_tracer"),
    "get_langfuse_tracing_status": ("cobweaverclaw_compress.observability", "get_langfuse_tracing_status"),
    "get_otel_metrics": ("cobweaverclaw_compress.observability", "get_otel_metrics"),
    "get_otel_metrics_status": ("cobweaverclaw_compress.observability", "get_otel_metrics_status"),
    "reset_cobweaverclaw_compress_tracing": ("cobweaverclaw_compress.observability", "reset_cobweaverclaw_compress_tracing"),
    "reset_otel_metrics": ("cobweaverclaw_compress.observability", "reset_otel_metrics"),
    # One-function API
    "compress": ("cobweaverclaw_compress.compress", "compress"),
    "compress_spreadsheet": ("cobweaverclaw_compress.compress", "compress_spreadsheet"),
    # Hooks
    "CompressionHooks": ("cobweaverclaw_compress.hooks", "CompressionHooks"),
    "CompressContext": ("cobweaverclaw_compress.hooks", "CompressContext"),
    "CompressEvent": ("cobweaverclaw_compress.hooks", "CompressEvent"),
    # Canonical pipeline
    "PipelineStage": ("cobweaverclaw_compress.pipeline", "PipelineStage"),
    "PipelineEvent": ("cobweaverclaw_compress.pipeline", "PipelineEvent"),
    "PipelineExtensionManager": ("cobweaverclaw_compress.pipeline", "PipelineExtensionManager"),
    "CANONICAL_PIPELINE_STAGES": ("cobweaverclaw_compress.pipeline", "CANONICAL_PIPELINE_STAGES"),
    # Shared context
    "SharedContext": ("cobweaverclaw_compress.shared_context", "SharedContext"),
}

# Memory remains optional and preserves the long-standing behavior of exposing
# `None` when the extra dependencies are not installed.
_OPTIONAL_EXPORTS = {
    "with_memory": ("cobweaverclaw_compress.memory", "with_memory"),
    "Memory": ("cobweaverclaw_compress.memory", "Memory"),
    "ScopeLevel": ("cobweaverclaw_compress.memory", "ScopeLevel"),
    "HierarchicalMemory": ("cobweaverclaw_compress.memory", "HierarchicalMemory"),
    "MemoryConfig": ("cobweaverclaw_compress.memory", "MemoryConfig"),
    "EmbedderBackend": ("cobweaverclaw_compress.memory", "EmbedderBackend"),
}


def __getattr__(name: str) -> Any:
    """Resolve package exports lazily while preserving legacy import paths."""
    module_attr = _LAZY_EXPORTS.get(name)
    if module_attr is not None:
        module_name, attr_name = module_attr
        value = getattr(import_module(module_name), attr_name)
        globals()[name] = value
        return value

    optional_module_attr = _OPTIONAL_EXPORTS.get(name)
    if optional_module_attr is not None:
        module_name, attr_name = optional_module_attr
        try:
            value = getattr(import_module(module_name), attr_name)
        except ImportError:
            value = None
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
