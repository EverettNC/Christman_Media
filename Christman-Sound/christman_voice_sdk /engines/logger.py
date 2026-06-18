"""Logger compatibility bridge for Christman Voice SDK engines.

Some engine modules are imported as `christman_voice_sdk.engines.*`; older
modules import them as top-level `engines.*`. Support both import modes.
"""

try:
    from ..utils.logger import Logger, get_logger, logger
except ImportError:
    from utils.logger import Logger, get_logger, logger

__all__ = ["Logger", "get_logger", "logger"]
