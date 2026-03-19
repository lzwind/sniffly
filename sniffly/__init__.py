"""Sniffly - Claude Code Analytics Dashboard"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("sniffly-iceleaf916")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development mode
    __version__ = "0.2.2"

__all__ = ["__version__"]
