from unittest.mock import Mock, patch

import httpx
import pytest

from api_client import APIError, ScoutAPI


def make_response(status_code=200, payload=None):
    request = httpx.Request("GET", "http://test.local")
    return httpx.Response(status_code, json=payload or {}, request=request)


@patch("api_client.httpx.request")
def test_login_posts_credentials(mock_request):
    mock_request.return_value = make_response(
        200, {"access_token": "test-token", "token_type": "bearer"}
    )
    client = ScoutAPI("http://test.local")

    result = client.login("scout_user", "example-password")

    assert result["access_token"] == "test-token"
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "http://test.local/auth/token"
    assert kwargs["json"] == {
        "username": "scout_user",
        "password": "example-password",
    }


@patch("api_client.httpx.request")
def test_current_user_sends_bearer_token(mock_request):
    mock_request.return_value = make_response(200, {"username": "scout_user"})
    client = ScoutAPI("http://test.local", token="test-token")

    result = client.get_current_user()

    assert result["username"] == "scout_user"
    assert mock_request.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


def test_authenticated_request_without_token_fails_before_network_call():
    client = ScoutAPI("http://test.local")

    with pytest.raises(APIError, match="sign in"):
        client.get_current_user()


@patch("api_client.httpx.request")
def test_ask_trims_question_and_posts_bearer_token(mock_request):
    mock_request.return_value = make_response(
        200,
        {
            "answer": "Answer based on evidence.",
            "sufficient_evidence": True,
            "sources": [],
            "research_query_id": 42,
        },
    )
    client = ScoutAPI("http://test.local", token="test-token")

    result = client.ask("  What does this notice require?  ")

    assert result["research_query_id"] == 42
    assert mock_request.call_args.kwargs["json"] == {
        "question": "What does this notice require?"
    }
    assert mock_request.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.parametrize("question", ["", "no", "x" * 2001])
def test_ask_rejects_invalid_question_length(question):
    client = ScoutAPI("http://test.local", token="test-token")

    with pytest.raises(APIError):
        client.ask(question)


@patch("api_client.httpx.request")
def test_401_returns_clear_authentication_error(mock_request):
    mock_request.return_value = make_response(401, {"detail": "Not authenticated"})
    client = ScoutAPI("http://test.local", token="expired-token")

    with pytest.raises(APIError) as exc_info:
        client.get_current_user()

    assert exc_info.value.status_code == 401
    assert "sign in again" in exc_info.value.user_message


@patch("api_client.httpx.request")
def test_timeout_has_user_friendly_message(mock_request):
    mock_request.side_effect = httpx.ReadTimeout(
        "timed out", request=httpx.Request("POST", "http://test.local/ask")
    )
    client = ScoutAPI("http://test.local", token="test-token")

    with pytest.raises(APIError, match="took too long"):
        client.ask("What does this notice require?")
