"""
Catan bot package.

Exports models and the Ollama integration for external use.
"""

from . import models  # noqa: F401
from .ollama_client import OllamaClient  # noqa: F401

__all__ = ["models", "OllamaClient"]

