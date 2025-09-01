import importlib.metadata

from ._bufferer import Bufferer

__version__ = importlib.metadata.version("bufferer")

__all__ = ["Bufferer"]
