"""Structured JSON logging + request IDs (stdlib only, no extra dependency)."""
import json
import logging
import sys
import time
import uuid

logger = logging.getLogger("netmind")
_access = logging.getLogger("netmind.access")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # we emit our own access logs


def log_event(event: str, **fields) -> None:
    logger.info(event, extra={"netmind_fields": fields})


class RequestIdAndAccessLogMiddleware:
    """Adds X-Request-ID to every response and logs one JSON access line per request.

    Privacy: only method/path/status/duration are logged — never request bodies or prompt content.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            path = scope.get("path", "")
            method = scope.get("method", "")
            _access.info(
                "%s %s -> %s (%s ms)",
                method,
                path,
                status_holder["status"],
                duration_ms,
                extra={"request_id": request_id, "http_status": status_holder["status"]},
            )
