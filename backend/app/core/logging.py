import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if settings.environment == "development" else logging.INFO)

    # Quiet noisy third-party loggers.
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
