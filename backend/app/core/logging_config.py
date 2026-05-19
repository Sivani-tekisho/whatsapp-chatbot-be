"""Logging setup — clear WhatsApp actions, quiet dashboard polling."""

import logging
import sys


class _HideWebhookStatusPollFilter(logging.Filter):
    """Stop /webhook/status from flooding the terminal (UI refresh only)."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "/webhook/status" in msg:
            return False
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    )
    handler.addFilter(_HideWebhookStatusPollFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    for name in ("uvicorn.access", "uvicorn.error"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False


def wa_log(logger: logging.Logger, action: str, detail: str = "") -> None:
    """WhatsApp-prefixed log line for easy scanning."""
    line = f"[WHATSAPP] {action}"
    if detail:
        line = f"{line} | {detail}"
    logger.info(line)
