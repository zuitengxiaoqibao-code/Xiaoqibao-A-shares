import logging

from qibao_desktop.logging_config import configure_desktop_logging


def test_desktop_logging_suppresses_per_request_http_logs(tmp_path) -> None:
    root = logging.getLogger()
    previous_handlers = tuple(root.handlers)
    previous_level = root.level
    httpx = logging.getLogger("httpx")
    httpcore = logging.getLogger("httpcore")
    previous_httpx_level = httpx.level
    previous_httpcore_level = httpcore.level
    try:
        configure_desktop_logging(tmp_path)

        assert httpx.level == logging.WARNING
        assert httpcore.level == logging.WARNING
    finally:
        for handler in tuple(root.handlers):
            handler.close()
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)
        httpx.setLevel(previous_httpx_level)
        httpcore.setLevel(previous_httpcore_level)
