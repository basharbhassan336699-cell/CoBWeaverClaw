"""Handler mixins for CoBWeaverClawProxy.

Each mixin class contains methods extracted from CoBWeaverClawProxy that handle
requests for a specific provider or concern. The mixins rely on CoBWeaverClawProxy's
__init__ for all self.* attributes (duck typing).
"""

from cobweaverclaw_compress.proxy.handlers.anthropic import AnthropicHandlerMixin
from cobweaverclaw_compress.proxy.handlers.batch import BatchHandlerMixin
from cobweaverclaw_compress.proxy.handlers.bedrock import BedrockHandlerMixin
from cobweaverclaw_compress.proxy.handlers.gemini import GeminiHandlerMixin
from cobweaverclaw_compress.proxy.handlers.openai import OpenAIHandlerMixin
from cobweaverclaw_compress.proxy.handlers.streaming import StreamingMixin

__all__ = [
    "AnthropicHandlerMixin",
    "BatchHandlerMixin",
    "BedrockHandlerMixin",
    "GeminiHandlerMixin",
    "OpenAIHandlerMixin",
    "StreamingMixin",
]
