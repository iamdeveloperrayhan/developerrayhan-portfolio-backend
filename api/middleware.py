"""
B-19. Custom middleware.

Logs every request as ``METHOD /path -> status (xx ms)`` and adds an
``X-Response-Time`` header to every response.
"""
import logging
import time

logger = logging.getLogger("api.request")


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response["X-Response-Time"] = f"{elapsed_ms:.0f}ms"
        logger.info(
            "%s %s -> %s (%.0f ms)",
            request.method,
            request.get_full_path(),
            response.status_code,
            elapsed_ms,
        )
        return response
