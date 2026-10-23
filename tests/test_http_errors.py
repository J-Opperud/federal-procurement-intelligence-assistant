
import httpx
import pytest

from app.services.http_errors import translate_http_error


@pytest.mark.parametrize(
    ("exception", "status_code", "code"),
    [
        (
            httpx.ReadTimeout("private details"),
            504,
            "EXTERNAL_SERVICE_TIMEOUT",
        ),
        (
            httpx.ConnectError(
                "private details",
                request=httpx.Request("GET", "https://example.com"),
            ),
            502,
            "EXTERNAL_SERVICE_CONNECTION_FAILED",
        ),
    ],
)
def test_transport_errors_are_safe(exception, status_code, code):
    translated = translate_http_error(exception)

    assert translated.status_code == status_code
    assert translated.code == code
    assert "private details" not in translated.detail


@pytest.mark.parametrize(
    ("upstream_status", "expected_status", "expected_code"),
    [
        (429, 429, "EXTERNAL_SERVICE_RATE_LIMIT"),
        (500, 502, "EXTERNAL_SERVICE_UNAVAILABLE"),
        (503, 502, "EXTERNAL_SERVICE_UNAVAILABLE"),
        (401, 502, "EXTERNAL_SERVICE_REQUEST_FAILED"),
    ],
)
def test_http_status_errors_are_standardized(
    upstream_status,
    expected_status,
    expected_code,
):
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(upstream_status, request=request)
    exception = httpx.HTTPStatusError(
        "private response details",
        request=request,
        response=response,
    )

    translated = translate_http_error(exception)

    assert translated.status_code == expected_status
    assert translated.code == expected_code
    assert "private response details" not in translated.detail
