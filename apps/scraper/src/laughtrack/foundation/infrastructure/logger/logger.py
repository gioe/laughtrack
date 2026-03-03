"""Infrastructure logging utilities.

Noise reduction goals:
- Only important messages go to the terminal by default (WARNING+)
- Full, detailed logs go to a rotating file handler (DEBUG+)
- Include scraper/club context inline without crashing if missing
"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Dict, Optional
import contextvars
from contextlib import contextmanager

from laughtrack.foundation.models.log_level import LogLevel
from laughtrack.foundation.models.types import JSONDict


class SafeExtraFormatter(logging.Formatter):
    """A formatter that safely fills in missing keys from `extra`.

    Standard logging raises a KeyError if the format string references a key
    that isn't present on the LogRecord. This formatter substitutes '-' for
    any missing key so we can freely reference optional context fields like
    club_name or scraper.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Provide safe defaults for optional fields
        defaults = {
            "club_id": "-",
            "club_name": "-",
            "scraper": "-",
            "scraping_url": "-",
            "timezone": "-",
            "popularity": "-",
        }

        for k, v in defaults.items():
            if not hasattr(record, k):
                setattr(record, k, v)

        return super().format(record)


class Logger:
    """
    Infrastructure utility for consistent logging across the application.
    """

    _loggers: Dict[str, logging.Logger] = {}
    _configured = False
    # Context variable holding current default logging context (per task)
    _context: contextvars.ContextVar = contextvars.ContextVar("lt_log_context", default={})

    class _ContextInjectFilter(logging.Filter):
        """Filter that injects task-local context into every LogRecord."""

        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            try:
                ctx = Logger._context.get()
                if isinstance(ctx, dict):
                    for k, v in ctx.items():
                        if not hasattr(record, k):
                            setattr(record, k, v)
            except Exception:
                # Never block logging due to context issues
                pass
            return True

    @classmethod
    def configure(
        cls,
        level: str = "INFO",
        format_string: Optional[str] = None,
        include_timestamp: bool = True,
        log_dir: Optional[str] = None,
    ) -> None:
        """
        Configure global logging settings.

        Args:
            level: Default log level
            format_string: Custom format string
            include_timestamp: Whether to include timestamps
            log_dir: Directory to write rotating log files (defaults to logs/main)
        """
        if cls._configured:
            return

        # Determine console/file levels from env (console defaults to WARNING to cut noise)
        console_level = os.getenv("LAUGHTRACK_LOG_CONSOLE_LEVEL", "WARNING").upper()
        file_level = os.getenv("LAUGHTRACK_LOG_FILE_LEVEL", "DEBUG").upper()

        # Default formats (include context safely)
        if format_string is None:
            if include_timestamp:
                # Compact human-readable console format emphasizing context
                format_string = (
                    "%(asctime)s | %(levelname)s | pid=%(process)d | club=%(club_name)s | scraper=%(scraper)s | %(message)s"
                )
            else:
                format_string = (
                    "%(levelname)s | pid=%(process)d | club=%(club_name)s | scraper=%(scraper)s | %(message)s"
                )

        file_format_string = (
            "%(asctime)s | %(levelname)s | pid=%(process)d | %(name)s | club_id=%(club_id)s club=%(club_name)s "
            "scraper=%(scraper)s | %(message)s"
        )

        # Build handlers explicitly instead of basicConfig
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)  # Let handlers filter by level

        # Clear any pre-existing handlers to avoid duplicate logs
        for h in list(root.handlers):
            root.removeHandler(h)

        # Console handler (reduced noise by default)
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(getattr(logging, console_level, logging.WARNING))
        console_handler.setFormatter(SafeExtraFormatter(format_string))
        # Inject context into records for this handler
        console_handler.addFilter(Logger._ContextInjectFilter())
        root.addHandler(console_handler)

        # File handler (full detail, rotating daily, keep 7 days)
        try:
            resolved_log_dir = log_dir or os.getenv("LAUGHTRACK_LOG_DIR", os.path.join("logs", "main"))
            os.makedirs(resolved_log_dir, exist_ok=True)
            file_path = os.path.join(resolved_log_dir, os.getenv("LAUGHTRACK_LOG_FILE", "app.log"))
            file_handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=7, encoding="utf-8")
            file_handler.setLevel(getattr(logging, file_level, logging.DEBUG))
            file_handler.setFormatter(SafeExtraFormatter(file_format_string))
            file_handler.addFilter(Logger._ContextInjectFilter())
            root.addHandler(file_handler)
        except Exception as e:
            # If file handler fails, fall back to console-only and warn once
            fallback_logger = logging.getLogger(__name__)
            fallback_logger.warning(f"File logging disabled due to error: {e}")

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str = __name__) -> logging.Logger:
        """
        Get or create a logger instance.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)

        return cls._loggers[name]

    # ---- Context management -------------------------------------------------
    @classmethod
    def push_context(cls, context: JSONDict):
        """Merge and push a context for the current task; returns a token to pop.

        Usage:
            token = Logger.push_context({"club_name": "Foo", "scraper": "bar"})
            try:
                ...
            finally:
                Logger.pop_context(token)
        """
        current = cls._context.get()
        merged = {**(current or {}), **(context or {})}
        return cls._context.set(merged)

    @classmethod
    def pop_context(cls, token) -> None:
        """Restore previous context using the token returned by push_context."""
        try:
            cls._context.reset(token)
        except Exception:
            pass

    @classmethod
    @contextmanager
    def use_context(cls, context: JSONDict):
        """Context manager to apply logging context within a block."""
        token = cls.push_context(context)
        try:
            yield
        finally:
            cls.pop_context(token)

    @classmethod
    def debug(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Log debug message."""
        logger = cls.get_logger(logger_name)
        logger.debug(message, extra=context or {})

    @classmethod
    def info(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Log info message."""
        logger = cls.get_logger(logger_name)
        logger.info(message, extra=context or {})

    @classmethod
    def warning(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Log warning message."""
        logger = cls.get_logger(logger_name)
        logger.warning(message, extra=context or {})

    @classmethod
    def warn(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Alias for warning method."""
        cls.warning(message, context, logger_name)

    @classmethod
    def error(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Log error message."""
        logger = cls.get_logger(logger_name)
        logger.error(message, extra=context or {})

    @classmethod
    def critical(cls, message: str, context: Optional[JSONDict] = None, logger_name: str = __name__) -> None:
        """Log critical message."""
        logger = cls.get_logger(logger_name)
        logger.critical(message, extra=context or {})

    @classmethod
    def write_log(
        cls, message: str, level: LogLevel, context: Optional[JSONDict] = None, logger_name: str = __name__
    ) -> None:
        """
        Write log message with specified level.

        Args:
            message: Message to log
            level: Log level
            context: Optional context data
            logger_name: Logger name to use
        """
        method_map = {
            LogLevel.DEBUG: cls.debug,
            LogLevel.INFO: cls.info,
            LogLevel.WARN: cls.warning,
            LogLevel.ERROR: cls.error,
            LogLevel.CRITICAL: cls.critical,
        }

        method = method_map.get(level, cls.info)
        method(message, context, logger_name)

    @classmethod
    def log_exception(cls, exception: Exception, logger_name: str = __name__) -> None:
        """Log an exception with traceback, preserving active context."""
        import traceback

        logger = cls.get_logger(logger_name)
        extra_ctx = cls._context.get() or {}
        logger.error(f"Exception occurred: {str(exception)}", exc_info=True, extra=extra_ctx)

    @classmethod
    def log_performance(cls, operation: str, duration: float, logger_name: str = __name__) -> None:
        """
        Log performance metrics.

        Args:
            operation: Name of operation
            duration: Duration in seconds
            logger_name: Logger name to use
        """
        cls.info(f"Performance: {operation} took {duration:.2f}s", logger_name=logger_name)

    @classmethod
    def log_with_timestamp(cls, message: str, level: LogLevel = LogLevel.INFO, logger_name: str = __name__) -> None:
        """
        Log message with explicit timestamp.

        Args:
            message: Message to log
            level: Log level
            logger_name: Logger name to use
        """
        timestamp = datetime.now().isoformat()
        timestamped_message = f"[{timestamp}] {message}"
        cls.write_log(timestamped_message, level, logger_name=logger_name)

    @classmethod
    def set_level(cls, level: str, logger_name: Optional[str] = None) -> None:
        """
        Set log level for a specific logger or all loggers.

        Args:
            level: Log level name
            logger_name: Specific logger name, or None for all
        """
        log_level = getattr(logging, level.upper())

        if logger_name:
            logger = cls.get_logger(logger_name)
            logger.setLevel(log_level)
        else:
            # Set for root logger
            logging.getLogger().setLevel(log_level)
