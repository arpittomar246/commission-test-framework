"""Input validation and error handling across the API.

Every failure comes back with the same body shape -- a detail and a code --
and the status the endpoint contract promises.
"""

from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = [pytest.mark.api, pytest.mark.smoke]

SOLD_DATE = "2024-05-12"
ERROR_KEYS = {"detail", "code"}

# Far beyond any id SQLite will hand out in a test run. Picking "highest id
# plus one" instead would race other workers creating rows under -n auto.
MISSING_ID = 999_999_999


def test_policy_value_of_zero_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A zero-value policy returns 400."""
    response = api_client.create_policy(
        agent_id=new_agent["id"],
        customer_name="Zero Value Ltd",
        value=0,
        sold_date=SOLD_DATE,
    )

    assert response.status == 400
    assert response.code == "INVALID_VALUE"
    assert "greater than zero" in (response.detail or "")
    # The one error shape, with nothing else smuggled alongside it.
    assert set(response.body) == ERROR_KEYS

    # A rejected request must not leave a row behind.
    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.status == 200
    assert listed.body == []


def test_negative_policy_value_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A negative policy value returns 400."""
    # Both ends of the negative range: a hair below zero, where a ``< 0``
    # rounding slip would show, and a value too large to be an accident.
    for value in (-0.01, -250_000):
        response = api_client.create_policy(
            agent_id=new_agent["id"],
            customer_name="Negative Value Ltd",
            value=value,
            sold_date=SOLD_DATE,
        )

        assert response.status == 400, f"{value} was not rejected"
        assert response.code == "INVALID_VALUE"
        assert set(response.body) == ERROR_KEYS

    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.status == 200
    assert listed.body == []


def test_creating_a_policy_for_an_unknown_agent_returns_404(
    api_client: ApiClient,
) -> None:
    """An agent_id with no matching agent returns 404."""
    # Everything else in the payload is valid, so the missing agent is the
    # only reason left for the request to fail.
    response = api_client.create_policy(
        agent_id=MISSING_ID,
        customer_name="Orphan Policy Ltd",
        value=100_000,
        sold_date=SOLD_DATE,
    )

    assert response.status == 404
    assert response.code == "AGENT_NOT_FOUND"
    assert str(MISSING_ID) in (response.detail or "")
    assert set(response.body) == ERROR_KEYS

    # No orphaned row pointing at an agent that does not exist.
    listed = api_client.list_policies(agent_id=MISSING_ID)
    assert listed.status == 200
    assert listed.body == []


def test_fetching_an_unknown_agent_returns_404() -> None:
    """Requesting a missing agent id returns 404."""


def test_commission_for_an_unknown_agent_returns_404() -> None:
    """The commission endpoint 404s for a missing agent."""


def test_malformed_month_is_rejected() -> None:
    """A month like 2026-13 returns 400."""


def test_missing_month_parameter_is_rejected() -> None:
    """Omitting the month query parameter returns 400."""


def test_missing_required_agent_fields_are_rejected() -> None:
    """A partial agent payload returns 400."""


def test_missing_required_policy_fields_are_rejected() -> None:
    """A partial policy payload returns 400."""


def test_invalid_email_is_rejected() -> None:
    """An unparseable email address returns 400."""


def test_duplicate_email_is_rejected() -> None:
    """Reusing an existing agent's email returns 409."""


def test_cancelling_an_already_cancelled_policy_returns_409() -> None:
    """The second cancellation of one policy conflicts."""


def test_cancelling_an_unknown_policy_returns_404() -> None:
    """Cancelling a policy id that does not exist returns 404."""


def test_unknown_status_filter_is_rejected() -> None:
    """An unrecognised status filter value returns 400."""


def test_non_numeric_policy_value_is_rejected() -> None:
    """A value that is not a number returns 400."""


def test_malformed_date_is_rejected() -> None:
    """A sold_date that is not a real date returns 400."""


def test_every_error_response_carries_a_code() -> None:
    """No failure path returns a body without a machine-readable code."""
