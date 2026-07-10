"""LangChain integration for CoBWeaverClaw.

This package provides seamless integration with LangChain, including:
- CoBWeaverClawChatModel: Drop-in wrapper for any LangChain chat model
- CoBWeaverClawChatMessageHistory: Automatic conversation compression
- CoBWeaverClawDocumentCompressor: Relevance-based document filtering
- CoBWeaverClawToolWrapper: Tool output compression for agents
- StreamingMetricsTracker: Token counting during streaming
- CoBWeaverClawLangSmithCallbackHandler: LangSmith trace enrichment
- compress_tool_messages: LangGraph pre-model hook for ToolMessage compression
- create_compress_tool_messages_node: LangGraph node factory

Example:
    from langchain_openai import ChatOpenAI
    from cobweaverclaw_compress.integrations.langchain import CoBWeaverClawChatModel

    # Wrap any LangChain model
    llm = CoBWeaverClawChatModel(ChatOpenAI(model="gpt-4o"))

    # Use like normal - optimization happens automatically
    response = llm.invoke("Hello!")

Install: pip install cobweaverclaw_compress[langchain]
"""

# Agent tool wrapping
from .agents import (
    CoBWeaverClawToolWrapper,
    ToolCompressionMetrics,
    ToolMetricsCollector,
    get_tool_metrics,
    reset_tool_metrics,
    wrap_tools_with_cobweaverclaw_compress,
)

# Core chat model wrapper
from .chat_model import (
    CoBWeaverClawCallbackHandler,
    CoBWeaverClawChatModel,
    CoBWeaverClawRunnable,
    OptimizationMetrics,
    langchain_available,
    optimize_messages,
)

# LangGraph integration
from .langgraph import (
    CompressToolMessagesConfig,
    CompressToolMessagesResult,
    ToolMessageCompressionMetrics,
    compress_tool_messages,
    create_compress_tool_messages_node,
)

# LangSmith integration
from .langsmith import (
    CoBWeaverClawLangSmithCallbackHandler,
    is_langsmith_available,
    is_langsmith_tracing_enabled,
)

# Memory integration
from .memory import CoBWeaverClawChatMessageHistory

# Provider auto-detection
from .providers import (
    detect_provider,
    get_cobweaverclaw_compress_provider,
    get_model_name_from_langchain,
)

# Retriever integration
from .retriever import CompressionMetrics, CoBWeaverClawDocumentCompressor

# Streaming metrics
from .streaming import (
    StreamingMetrics,
    StreamingMetricsCallback,
    StreamingMetricsTracker,
    track_async_streaming_response,
    track_streaming_response,
)

__all__ = [
    # Core
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
    # LangGraph
    "compress_tool_messages",
    "create_compress_tool_messages_node",
    "CompressToolMessagesConfig",
    "CompressToolMessagesResult",
    "ToolMessageCompressionMetrics",
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
]
