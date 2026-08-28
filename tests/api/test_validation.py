"""Input validation and error handling across the API.

Every failure comes back with the same body shape -- a detail and a code --
and the status the endpoint contract promises.
"""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def test_policy_value_of_zero_is_rejected() -> None:
    """A zero-value policy returns 400."""


def test_negative_policy_value_is_rejected() -> None:
    """A negative policy value returns 400."""


def test_creating_a_policy_for_an_unknown_agent_returns_404() -> None:
    """An agent_id with no matching agent returns 404."""


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
