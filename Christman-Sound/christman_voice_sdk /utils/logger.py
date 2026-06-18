"""
Logging system for ICanHearYou.

Provides structured logging with color output and file rotation.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console


class Logger:
    """Custom logger with rich console output and file logging."""

    def __init__(
        self,
        name: str,
        log_dir: Optional[Path] = None,
        level: str = "INFO",
        file_logging: bool = True
    ):
        """Initialize logger.

        Args:
            name: Logger name
            log_dir: Directory for log files
            level: Logging level
            file_logging: Whether to enable file logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Rich console handler
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        console_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(console_handler)

        # File handler if enabled
        if file_logging and log_dir:
            log_dir = Path(log_dir)
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / f"{name}.log"
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5
                )
                file_handler.setLevel(logging.DEBUG)

                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except OSError:
                self.logger.warning(
                    "File logging disabled; could not write log directory: %s",
                    log_dir,
                    exc_info=True,
                )

    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        self.logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Log info message."""
        self.logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Log warning message."""
        self.logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """Log error message."""
        self.logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """Log critical message."""
        self.logger.critical(msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(msg, **kwargs)


def get_logger(name: str, **kwargs) -> Logger:
    """Get or create a logger instance.

    Args:
        name: Logger name
        **kwargs: Additional arguments for Logger

    Returns:
        Logger instance
    """
    return Logger(name, **kwargs)


# === EXPORT THE SEXY GOODS ===
# Primary way most files will import you
logger = get_logger(
    name="christman_voice_sdk",
    log_dir=Path.home() / ".christman_ai" / "logs",
    level="DEBUG",
    file_logging=True
)

# One-liner every module in the ark will ride
__all__ = ["logger", "get_logger", "Logger"]
