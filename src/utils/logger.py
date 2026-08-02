"""Structured logging for analyzer."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir: Path = None, level: int = logging.INFO) -> logging.Logger:
    """Configure logging with file and console handlers."""
    if log_dir is None:
        log_dir = Path("logs")

    log_dir.mkdir(parents=True, exist_ok=True)

    # Main logger
    logger = logging.getLogger("insta360_analyzer")
    logger.setLevel(level)

    # Formatters
    detailed_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_format = logging.Formatter(
        "%(levelname)s - %(message)s",
    )

    # File handler (detailed)
    main_file = log_dir / "main.log"
    fh = logging.FileHandler(main_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(detailed_format)
    logger.addHandler(fh)

    # Error file handler
    error_file = log_dir / "errors.log"
    eh = logging.FileHandler(error_file)
    eh.setLevel(logging.ERROR)
    eh.setFormatter(detailed_format)
    logger.addHandler(eh)

    # Console handler (simple)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(simple_format)
    logger.addHandler(ch)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    return logging.getLogger(f"insta360_analyzer.{name}")


class ContextualLogger:
    """Logger wrapper that adds file_id and stage context."""

    def __init__(self, base_logger: logging.Logger, file_id: str = None, stage: str = None):
        self.logger = base_logger
        self.file_id = file_id
        self.stage = stage

    def _format_msg(self, msg: str) -> str:
        context_parts = []
        if self.file_id:
            context_parts.append(f"[{self.file_id}]")
        if self.stage:
            context_parts.append(f"<{self.stage}>")
        if context_parts:
            return f"{' '.join(context_parts)} {msg}"
        return msg

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(self._format_msg(msg), *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(self._format_msg(msg), *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(self._format_msg(msg), *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(self._format_msg(msg), *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(self._format_msg(msg), *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(self._format_msg(msg), *args, **kwargs)
