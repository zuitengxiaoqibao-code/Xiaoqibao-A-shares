import httpx

from qibao_api.ai_status import classify_ai_status, classify_ai_exception


def test_ai_status_distinguishes_configuration_from_runtime_failures() -> None:
    assert classify_ai_status(configured=False).state == "unconfigured"
    assert classify_ai_status(configured=True).state == "configured_unverified"
    assert classify_ai_status(configured=True, verified=True).state == "connected"
    assert classify_ai_status(configured=True, error=TimeoutError()).state == "timeout"
    assert classify_ai_status(configured=True, http_status=429).state == "rate_limited"
    assert classify_ai_status(configured=True, http_status=404).state == "model_not_found"
    assert classify_ai_status(configured=True, http_status=401).state == "connection_failed"


def test_ai_status_always_exposes_a_chinese_user_message() -> None:
    cases = (
        classify_ai_status(configured=False),
        classify_ai_status(configured=True),
        classify_ai_status(configured=True, verified=True),
        classify_ai_status(configured=True, error=TimeoutError()),
        classify_ai_status(configured=True, http_status=429),
        classify_ai_status(configured=True, http_status=404),
    )

    assert all(any("\u4e00" <= character <= "\u9fff" for character in item.message) for item in cases)


def test_ai_exception_status_preserves_http_and_timeout_reason() -> None:
    request = httpx.Request("POST", "https://ai.example/v1/chat/completions")
    assert classify_ai_exception(httpx.ReadTimeout("slow", request=request)).state == "timeout"
    assert classify_ai_exception(httpx.HTTPStatusError("limited", request=request, response=httpx.Response(429, request=request))).state == "rate_limited"
    assert classify_ai_exception(httpx.HTTPStatusError("missing", request=request, response=httpx.Response(404, request=request))).state == "model_not_found"
    assert classify_ai_exception(OSError("offline")).state == "connection_failed"
