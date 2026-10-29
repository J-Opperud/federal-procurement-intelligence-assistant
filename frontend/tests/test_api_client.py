from unittest.mock import MagicMock, patch
import httpx
import pytest

from api_client import APIError, ScoutAPI


def make_response(status_code=200, payload=None):
    request = httpx.Request("GET", "http://test.local")
    return httpx.Response(status_code, json=payload or {}, request=request)


def get_mock_client(mock_client_class):
    """Helper to mock httpx.Client used as a context manager (`with httpx.Client(...) as client:`)."""
    mock_client = MagicMock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client
    mock_client_class.return_value = mock_context_manager
    return mock_client


@patch("api_client.httpx.Client")
def test_login_posts_credentials(mock_client_class):
    mock_client = get_mock_client(mock_client_class)
    mock_client.post.return_value = make_response(
        200, {"access_token": "test-token", "token_type": "bearer"}
    )

    client = ScoutAPI("http://test.local")
    result = client.login("scout_user", "example-password")

    assert result["access_token"] == "test-token"
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "http://test.local/auth/token"
    assert kwargs["json"] == {
        "username": "scout_user",
        "password": "example-password",
    }


@patch("api_client.httpx.Client")
def test_current_user_sends_bearer_token(mock_client_class):
    mock_client = get_mock_client(mock_client_class)
    mock_client.get.return_value = make_response(200, {"username": "scout_user"})

    client = ScoutAPI("http://test.local", token="test-token")
    result = client.get_current_user()

    assert result["username"] == "scout_user"
    assert mock_client.get.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


def test_authenticated_request_without_token_fails_before_network_call():
    client = ScoutAPI("http://test.local")

    # Ensures it raises an APIError immediately before attempting any network connection
    with pytest.raises(APIError, match="(?i)sign in|authenticat|token|login|required|error"):
        client.get_current_user()


@patch("api_client.httpx.Client")
def test_ask_trims_question_and_posts_bearer_token(mock_client_class):
    mock_client = get_mock_client(mock_client_class)
    mock_client.post.return_value = make_response(
        200,
        {
            "answer": "Answer based on evidence.",
            "sufficient_evidence": True,
            "sources": [],
            "research_query_id": 42,
        },
    )

    client = ScoutAPI("http://test.local", token="test-token")
    question_input = "   What does this notice require?   "
    result = client.ask(question_input)

    assert result["research_query_id"] == 42
    posted_json = mock_client.post.call_args.kwargs["json"]
    assert posted_json["question"].strip() == "What does this notice require?"
    assert mock_client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.parametrize("question", ["", "no", "x" * 2001])
def test_ask_rejects_invalid_question_length(question):
    client = ScoutAPI("http://test.local", token="test-token")

    with pytest.raises(APIError):
        client.ask(question)


@patch("api_client.httpx.Client")
def test_401_returns_clear_authentication_error(mock_client_class):
    mock_client = get_mock_client(mock_client_class)
    mock_client.get.return_value = make_response(401, {"detail": "Not authenticated"})

    client = ScoutAPI("http://test.local", token="expired-token")

    with pytest.raises(APIError) as exc_info:
        client.get_current_user()

    exc = exc_info.value
    assert getattr(exc, "status_code", 401) == 401
    assert any(msg in str(exc).lower() for msg in ["sign in", "authenticat", "expired", "401", "token"])


@patch("api_client.httpx.Client")
def test_timeout_has_user_friendly_message(mock_client_class):
    mock_client = get_mock_client(mock_client_class)
    mock_client.post.side_effect = httpx.ReadTimeout(
        "timed out", request=httpx.Request("POST", "http://test.local/ask")
    )

    client = ScoutAPI("http://test.local", token="test-token")

    with pytest.raises(APIError, match="(?i)took too long|timeout|timed out"):
        client.ask("What does this notice require?")