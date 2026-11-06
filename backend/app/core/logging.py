"""Logging setup. Operational events only: never log passwords, tokens, API keys,
or financial details (amounts, descriptions)."""
import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Access logs include only method/path/status, which is fine.
    logging.getLogger("httpx").setLevel(logging.WARNING)
