
import pytest

from app.services.sam_gov import SamGovClient


@pytest.fixture
def client():
    return SamGovClient(api_key="mock-sam-api-key")


@pytest.mark.parametrize(
    ("posted_from", "posted_to"),
    [
        ("2026-10-01", "10/23/2026"),
        ("10/24/2026", "10/23/2026"),
        ("10/01/2025", "10/02/2026"),
    ],
)
def test_rejects_invalid_date_windows(client, posted_from, posted_to):
    with pytest.raises(ValueError):
        client.search_opportunities(
            posted_from=posted_from,
            posted_to=posted_to,
        )


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_rejects_invalid_limits(client, limit):
    with pytest.raises(ValueError, match="limit"):
        client.search_opportunities(
            posted_from="10/01/2026",
            posted_to="10/23/2026",
            limit=limit,
        )


def test_rejects_negative_offset(client):
    with pytest.raises(ValueError, match="offset"):
        client.search_opportunities(
            posted_from="10/01/2026",
            posted_to="10/23/2026",
            offset=-1,
        )


def test_accepts_valid_date_window_and_limits(monkeypatch, client):
    # Verify valid input reaches the HTTP request without calling SAM.gov.
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"totalRecords": 0, "opportunitiesData": []}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.sam_gov.httpx.Client",
        lambda **kwargs: FakeClient(),
    )

    result = client.search_opportunities(
        posted_from="10/23/2025",
        posted_to="10/23/2026",
        limit=1000,
        offset=0,
    )

    assert result["total_records"] == 0
