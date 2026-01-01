import logging
import sys


class ColoredFormatter(logging.Formatter):
    """A custom logging formatter that adds colors to log levels."""

    COLORS = {
        "WARNING": "\033[93m",  # Yellow
        "INFO": "\033[94m",  # Blue
        "DEBUG": "\033[92m",  # Green
        "CRITICAL": "\033[91m",  # Red
        "ERROR": "\033[91m",  # Red
        "SQL": "\033[90m",  # Magenta for SQL
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, datefmt: str | None = None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        log_message = super().format(record)
        # Special color for SQL logs
        if record.name == "sqlalchemy.engine.Engine":
            return f"{self.COLORS['SQL']}{log_message}{self.RESET}"

        # The levelname is already formatted, so we check the original level.
        original_levelname = record.levelname
        if original_levelname in self.COLORS:
            return f"{self.COLORS[original_levelname]}{log_message}{self.RESET}"
        return log_message


class SafeExtraFormatter(ColoredFormatter):
    def format(self, record):
        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            if not hasattr(record, field):
                setattr(record, field, "-")
        return super().format(record)


def setup_logging():
    log_level = logging.INFO

    log_format = (
        "%(asctime)s [%(levelname)-2s] [%(name)s] %(message)s | "
        "method=%(method)s path=%(path)s status=%(status_code)s "
        "duration_ms=%(duration_ms)s request_id=%(request_id)s"
    )

    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
    )

    formatter = SafeExtraFormatter(log_format, date_format)
    root_logger = logging.getLogger()
    root_logger.handlers[0].setFormatter(formatter)

    # SQLAlchemy logging
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.WARNING)
    sql_logger.propagate = False
