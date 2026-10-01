"""The test framework's own HTTP client.

These run without the app: the client's session is swapped for a stand-in that
answers every request the same way, so the client's behaviour is the only thing
under test. Marked ``api`` so the API job in CI picks them up.
"""

import pytest
import requests

from framework.api_client import ApiClient

pytestmark = pytest.mark.api


def _always(status: int):
    """A stand-in for ``Session.request`` that counts calls and returns ``status``."""
    calls: list[str] = []

    def request(method: str, url: str, **_: object) -> requests.Response:
        calls.append(method)
        response = requests.Response()
        response.status_code = status
        response._content = b"Internal Server Error"
        return response

    return request, calls


def test_a_failed_post_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 5xx on a write is reported once, never re-sent."""
    client = ApiClient(max_retries=2, retry_backoff=0.0)
    fake, calls = _always(500)
    monkeypatch.setattr(client.session, "request", fake)

    # A server can save a row and then fail while answering. Sending the POST
    # again would save it again, so the failure has to come straight back.
    response = client.create_policy(
        agent_id=1, customer_name="Once Only", value=100_000, sold_date="2024-05-12"
    )

    assert response.status == 500
    assert response.attempts == 1
    assert calls == ["POST"]

    # Control: reads are still retried, since asking twice changes nothing.
    calls.clear()
    read = client.get_agent(1)

    assert read.status == 500
    assert read.attempts == 3
    assert calls == ["GET", "GET", "GET"]
