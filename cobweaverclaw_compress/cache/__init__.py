"""CoBWeaverClaw Cache Optimization Module.

This module provides a plugin-based architecture for cache optimization
across different LLM providers. Each provider has different caching
mechanisms and this module abstracts those differences.

Provider Caching Differences:
- Anthropic: Explicit cache_control blocks, 90% savings, 5-min TTL
- OpenAI: Automatic prefix caching, 50% savings, no user control
- Google: Separate CachedContent API, 75% savings + storage costs

Usage:
    from cobweaverclaw_compress.cache import CacheOptimizerRegistry, SemanticCacheLayer

    # Get provider-specific optimizer
    optimizer = CacheOptimizerRegistry.get("anthropic")
    result = optimizer.optimize(messages, context)

    # With semantic caching layer
    semantic = SemanticCacheLayer(optimizer, similarity_threshold=0.95)
    result = semantic.process(messages, context)

    # Register custom optimizer
    CacheOptimizerRegistry.register("my-provider", MyOptimizer)
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Expose concrete types to static analysis while keeping runtime imports lazy.
    from cobweaverclaw_compress.cache.anthropic import AnthropicCacheOptimizer  # noqa: F401
    from cobweaverclaw_compress.cache.base import (  # noqa: F401
        BaseCacheOptimizer,
        CacheBreakpoint,
        CacheConfig,
        CacheMetrics,
        CacheOptimizer,
        CacheResult,
        CacheStrategy,
        OptimizationContext,
    )
    from cobweaverclaw_compress.cache.compression_cache import CompressionCache  # noqa: F401
    from cobweaverclaw_compress.cache.dynamic_detector import (  # noqa: F401
        DetectorConfig,
        DynamicCategory,
        DynamicContentDetector,
        DynamicSpan,
        detect_dynamic_content,
    )
    from cobweaverclaw_compress.cache.google import GoogleCacheOptimizer  # noqa: F401
    from cobweaverclaw_compress.cache.openai import OpenAICacheOptimizer  # noqa: F401
    from cobweaverclaw_compress.cache.prefix_tracker import (  # noqa: F401
        FreezeStats,
        PrefixCacheTracker,
        PrefixFreezeConfig,
        SessionTrackerStore,
    )
    from cobweaverclaw_compress.cache.registry import CacheOptimizerRegistry  # noqa: F401
    from cobweaverclaw_compress.cache.semantic import SemanticCache, SemanticCacheLayer  # noqa: F401

__all__ = [
    # Base types
    "BaseCacheOptimizer",
    "CacheBreakpoint",
    "CacheConfig",
    "CacheMetrics",
    "CacheOptimizer",
    "CacheResult",
    "CacheStrategy",
    "OptimizationContext",
    # Dynamic content detection
    "DetectorConfig",
    "DynamicCategory",
    "DynamicContentDetector",
    "DynamicSpan",
    "detect_dynamic_content",
    # Registry
    "CacheOptimizerRegistry",
    # Provider implementations
    "AnthropicCacheOptimizer",
    "OpenAICacheOptimizer",
    "GoogleCacheOptimizer",
    # Semantic caching
    "SemanticCacheLayer",
    "SemanticCache",
    # Compression cache (token cobweaverclaw_compress mode)
    "CompressionCache",
    # Prefix cache tracking
    "PrefixCacheTracker",
    "PrefixFreezeConfig",
    "FreezeStats",
    "SessionTrackerStore",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Base types
    "BaseCacheOptimizer": ("cobweaverclaw_compress.cache.base", "BaseCacheOptimizer"),
    "CacheBreakpoint": ("cobweaverclaw_compress.cache.base", "CacheBreakpoint"),
    "CacheConfig": ("cobweaverclaw_compress.cache.base", "CacheConfig"),
    "CacheMetrics": ("cobweaverclaw_compress.cache.base", "CacheMetrics"),
    "CacheOptimizer": ("cobweaverclaw_compress.cache.base", "CacheOptimizer"),
    "CacheResult": ("cobweaverclaw_compress.cache.base", "CacheResult"),
    "CacheStrategy": ("cobweaverclaw_compress.cache.base", "CacheStrategy"),
    "OptimizationContext": ("cobweaverclaw_compress.cache.base", "OptimizationContext"),
    # Dynamic content detection
    "DetectorConfig": ("cobweaverclaw_compress.cache.dynamic_detector", "DetectorConfig"),
    "DynamicCategory": ("cobweaverclaw_compress.cache.dynamic_detector", "DynamicCategory"),
    "DynamicContentDetector": ("cobweaverclaw_compress.cache.dynamic_detector", "DynamicContentDetector"),
    "DynamicSpan": ("cobweaverclaw_compress.cache.dynamic_detector", "DynamicSpan"),
    "detect_dynamic_content": ("cobweaverclaw_compress.cache.dynamic_detector", "detect_dynamic_content"),
    # Registry
    "CacheOptimizerRegistry": ("cobweaverclaw_compress.cache.registry", "CacheOptimizerRegistry"),
    # Provider implementations
    "AnthropicCacheOptimizer": ("cobweaverclaw_compress.cache.anthropic", "AnthropicCacheOptimizer"),
    "OpenAICacheOptimizer": ("cobweaverclaw_compress.cache.openai", "OpenAICacheOptimizer"),
    "GoogleCacheOptimizer": ("cobweaverclaw_compress.cache.google", "GoogleCacheOptimizer"),
    # Semantic caching
    "SemanticCacheLayer": ("cobweaverclaw_compress.cache.semantic", "SemanticCacheLayer"),
    "SemanticCache": ("cobweaverclaw_compress.cache.semantic", "SemanticCache"),
    # Compression cache
    "CompressionCache": ("cobweaverclaw_compress.cache.compression_cache", "CompressionCache"),
    # Prefix cache tracking
    "PrefixCacheTracker": ("cobweaverclaw_compress.cache.prefix_tracker", "PrefixCacheTracker"),
    "PrefixFreezeConfig": ("cobweaverclaw_compress.cache.prefix_tracker", "PrefixFreezeConfig"),
    "FreezeStats": ("cobweaverclaw_compress.cache.prefix_tracker", "FreezeStats"),
    "SessionTrackerStore": ("cobweaverclaw_compress.cache.prefix_tracker", "SessionTrackerStore"),
}


def __getattr__(name: str) -> object:
    if name == "__path__":
        raise AttributeError(name)

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
