import logging
import logging.config
import contextvars
import uuid
from pathlib import Path
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold request id for the current context
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_ctx.get()
        except Exception:
            record.request_id = "-"
        return True


DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    log_level = (level or DEFAULT_LOG_LEVEL).upper()

    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
        }
    }
    active_handlers = ["console"]

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10 MB por archivo
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "default",
            "filters": ["request_id"],
        }
        active_handlers.append("file")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": RequestIdFilter},
        },
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": handlers,
        "root": {
            "handlers": active_handlers,
            "level": log_level,
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects a unique request ID into the logging context for each request.

    Reads X-Request-ID from the incoming headers (useful when set by a gateway)
    or generates a new UUID. The ID is propagated via response header too.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
