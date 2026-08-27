"""Logging configuration for the MT5 AI Trader project.

Provides a centralised logging setup using ``loguru`` with dual output
to *stderr* (console) and a rotating log file.  The file rotation keeps
individual log files at 10 MB maximum and retains logs for 7 days.
"""

from __future__ import annotations

from loguru import logger

# Re-export the configured logger so consumers can do:
#   from utils.logging import logger
__all__ = ["logger", "setup_logging"]


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "./logs/trader.log",
) -> None:
    """Configure *loguru* with stderr and rotating file sinks.

    Removes the default loguru handler and registers two new sinks:

    1. **stderr** – coloured console output at *log_level*.
    2. **File** – plain-text file at *log_level* with rotation
       (10 MB per file, 7-day retention).

    Parameters
    ----------
    log_level:
        Minimum log level (e.g. ``"DEBUG"``, ``"INFO"``, ``"WARNING"``).
        Defaults to ``"INFO"``.
    log_file:
        Path to the log file.  Parent directories are created
        automatically if they do not exist.  Defaults to
        ``"./logs/trader.log"``.
    """
    # Remove the default loguru handler (id=0) to avoid duplicate output.
    logger.remove()

    # Console sink (coloured, stderr).
    logger.add(
        sink="<stderr>",
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File sink with rotation.
    logger.add(
        sink=log_file,
        level=log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation="10 MB",
        retention="7 days",
        enqueue=True,  # thread-safe async writing
        encoding="utf-8",
    )
