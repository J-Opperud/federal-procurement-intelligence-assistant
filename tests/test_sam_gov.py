
from unittest.mock import Mock

from app.services.sam_gov import SAM_API_BASE_URL, SamGovClient


def test_search_uses_official_https_endpoint(monkeypatch):
    mock_response = Mock()
    mock_response.json.return_value = {
        "totalRecords": 0,
        "opportunitiesData": [],
    }
    mock_response.raise_for_status.return_value = None

    mock_http_client = Mock()
    mock_http_client.get.return_value = mock_response

    class MockClientContext:
        def __enter__(self):
            return mock_http_client

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "app.services.sam_gov.httpx.Client",
        lambda **kwargs: MockClientContext(),
    )

    client = SamGovClient(api_key="mock-sam-api-key")
    result = client.search_opportunities(
        posted_from="10/01/2026",
        posted_to="10/23/2026",
        limit=100,
        offset=0,
    )

    assert SAM_API_BASE_URL.startswith("https://")
    mock_http_client.get.assert_called_once()
    args, kwargs = mock_http_client.get.call_args
    assert args[0] == SAM_API_BASE_URL
    assert kwargs["params"]["postedFrom"] == "10/01/2026"
    assert kwargs["params"]["postedTo"] == "10/23/2026"
    assert kwargs["params"]["limit"] == 100
    assert kwargs["params"]["offset"] == 0
    assert result["opportunities"] == []
