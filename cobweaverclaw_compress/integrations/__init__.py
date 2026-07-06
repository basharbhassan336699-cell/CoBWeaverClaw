"""CoBWeaverClaw integrations with popular LLM frameworks.

Available integrations:

LangChain (pip install cobweaverclaw_compress[langchain]):
    - CoBWeaverClawChatModel: Drop-in wrapper for any LangChain chat model
    - CoBWeaverClawChatMessageHistory: Automatic conversation compression
    - CoBWeaverClawDocumentCompressor: Relevance-based document filtering
    - CoBWeaverClawToolWrapper: Tool output compression for agents
    - StreamingMetricsTracker: Token counting during streaming
    - CoBWeaverClawLangSmithCallbackHandler: LangSmith trace enrichment

Agno (pip install agno):
    - CoBWeaverClawAgnoModel: Drop-in wrapper for any Agno model
    - CoBWeaverClawPreHook/CoBWeaverClawPostHook: Agent-level hooks for tracking
    - create_cobweaverclaw_compress_hooks: Convenience function to create hook pairs

MCP (Model Context Protocol):
    - CoBWeaverClawMCPCompressor: Compress MCP tool results
    - compress_tool_result: Simple function for tool compression

Example:
    # LangChain integration
    from cobweaverclaw_compress.integrations import CoBWeaverClawChatModel
    # or explicitly:
    from cobweaverclaw_compress.integrations.langchain import CoBWeaverClawChatModel

    # Agno integration
    from cobweaverclaw_compress.integrations.agno import CoBWeaverClawAgnoModel
    # or explicitly:
    from cobweaverclaw_compress.integrations.agno import CoBWeaverClawAgnoModel

    # MCP integration
    from cobweaverclaw_compress.integrations import compress_tool_result
    # or explicitly:
    from cobweaverclaw_compress.integrations.mcp import compress_tool_result
"""

# Re-export from langchain subpackage for backwards compatibility
from .langchain import (
    # Retrievers
    CompressionMetrics,
    # Core
    CoBWeaverClawCallbackHandler,
    # Memory
    CoBWeaverClawChatMessageHistory,
    CoBWeaverClawChatModel,
    CoBWeaverClawDocumentCompressor,
    # LangSmith
    CoBWeaverClawLangSmithCallbackHandler,
    CoBWeaverClawRunnable,
    # Agents
    CoBWeaverClawToolWrapper,
    OptimizationMetrics,
    # Streaming
    StreamingMetrics,
    StreamingMetricsCallback,
    StreamingMetricsTracker,
    ToolCompressionMetrics,
    ToolMetricsCollector,
    # Provider Detection
    detect_provider,
    get_cobweaverclaw_compress_provider,
    get_model_name_from_langchain,
    get_tool_metrics,
    is_langsmith_available,
    is_langsmith_tracing_enabled,
    langchain_available,
    optimize_messages,
    reset_tool_metrics,
    track_async_streaming_response,
    track_streaming_response,
    wrap_tools_with_cobweaverclaw_compress,
)

# Re-export from mcp subpackage for backwards compatibility
from .mcp import (
    DEFAULT_MCP_PROFILES,
    CoBWeaverClawMCPClientWrapper,
    CoBWeaverClawMCPCompressor,
    MCPCompressionResult,
    MCPToolProfile,
    compress_tool_result,
    compress_tool_result_with_metrics,
    create_cobweaverclaw_compress_mcp_proxy,
)

# Re-export from agno subpackage (optional dependency)
try:
    from .agno import (
        CoBWeaverClawAgnoModel,
        CoBWeaverClawPostHook,
        CoBWeaverClawPreHook,
        agno_available,
        create_cobweaverclaw_compress_hooks,
        get_model_name_from_agno,
    )
    from .agno import OptimizationMetrics as AgnoOptimizationMetrics
    from .agno import get_cobweaverclaw_compress_provider as get_agno_provider
    from .agno import optimize_messages as optimize_agno_messages

    _AGNO_AVAILABLE = True
except ImportError:
    _AGNO_AVAILABLE = False

__all__ = [
    # LangChain Core
    "CoBWeaverClawChatModel",
    "CoBWeaverClawCallbackHandler",
    "CoBWeaverClawRunnable",
    "OptimizationMetrics",
    "optimize_messages",
    "langchain_available",
    # Provider Detection
    "detect_provider",
    "get_cobweaverclaw_compress_provider",
    "get_model_name_from_langchain",
    # Memory
    "CoBWeaverClawChatMessageHistory",
    # Retrievers
    "CoBWeaverClawDocumentCompressor",
    "CompressionMetrics",
    # Agents
    "CoBWeaverClawToolWrapper",
    "ToolCompressionMetrics",
    "ToolMetricsCollector",
    "wrap_tools_with_cobweaverclaw_compress",
    "get_tool_metrics",
    "reset_tool_metrics",
    # LangSmith
    "CoBWeaverClawLangSmithCallbackHandler",
    "is_langsmith_available",
    "is_langsmith_tracing_enabled",
    # Streaming
    "StreamingMetricsTracker",
    "StreamingMetricsCallback",
    "StreamingMetrics",
    "track_streaming_response",
    "track_async_streaming_response",
    # MCP
    "CoBWeaverClawMCPCompressor",
    "CoBWeaverClawMCPClientWrapper",
    "MCPCompressionResult",
    "MCPToolProfile",
    "compress_tool_result",
    "compress_tool_result_with_metrics",
    "create_cobweaverclaw_compress_mcp_proxy",
    "DEFAULT_MCP_PROFILES",
    # Agno
    "CoBWeaverClawAgnoModel",
    "CoBWeaverClawPreHook",
    "CoBWeaverClawPostHook",
    "agno_available",
    "create_cobweaverclaw_compress_hooks",
    "get_agno_provider",
    "get_model_name_from_agno",
    "AgnoOptimizationMetrics",
    "optimize_agno_messages",
]
