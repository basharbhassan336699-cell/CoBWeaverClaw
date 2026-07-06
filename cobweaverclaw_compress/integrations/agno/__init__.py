"""Agno integration for CoBWeaverClaw SDK.

This module provides seamless integration with Agno (formerly Phidata),
enabling automatic context optimization for Agno agents.

Components:
1. CoBWeaverClawAgnoModel - Wraps any Agno model to apply CoBWeaverClaw transforms
2. create_cobweaverclaw_compress_hooks - Creates pre/post hooks for Agno agents
3. optimize_messages - Standalone function for manual optimization

Example:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from cobweaverclaw_compress.integrations.agno import CoBWeaverClawAgnoModel

    # Wrap any Agno model
    model = OpenAIChat(id="gpt-4o")
    optimized_model = CoBWeaverClawAgnoModel(model)

    # Use with agent
    agent = Agent(model=optimized_model)
    response = agent.run("Hello!")
"""

from .hooks import (
    CoBWeaverClawPostHook,
    CoBWeaverClawPreHook,
    HookMetrics,
    create_cobweaverclaw_compress_hooks,
)
from .model import (
    CoBWeaverClawAgnoModel,
    OptimizationMetrics,
    agno_available,
    optimize_messages,
)
from .providers import get_cobweaverclaw_compress_provider, get_model_name_from_agno

__all__ = [
    # Model wrapper
    "CoBWeaverClawAgnoModel",
    "OptimizationMetrics",
    "agno_available",
    "optimize_messages",
    # Hooks
    "create_cobweaverclaw_compress_hooks",
    "CoBWeaverClawPreHook",
    "CoBWeaverClawPostHook",
    "HookMetrics",
    # Provider detection
    "get_cobweaverclaw_compress_provider",
    "get_model_name_from_agno",
]
