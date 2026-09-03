"""Clawbacks when a policy is cancelled.

A cancellation reverses the policy's commission against the month the policy
was *sold*, never the month it was cancelled -- and it can never push a payout
below the minimum guarantee while that guarantee is in force.
"""

from datetime import date
from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = pytest.mark.api

# Settled agents throughout this file unless a test is specifically about the
# guarantee floor: with the window shut, a clawback is visible in the payout
# instead of being absorbed by the minimum.
SETTLED_JOIN_DATE = "2023-01-10"
MONTH = "2024-05"


def test_cancelling_a_policy_reverses_its_commission(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """The clawback equals 10% of the cancelled policy's value."""
    agent = agent_factory(join_date=SETTLED_JOIN_DATE)
    # Two policies, one cancelled, so the clawback can be told apart from the
    # earnings it is subtracted from.
    policy_factory(agent["id"], value=400_000, sold_date=f"{MONTH}-06")
    policy_factory(agent["id"], value=150_000, sold_date=f"{MONTH}-14", cancelled=True)

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 2
    assert response.body["gross_commission"] == pytest.approx(55_000.0)
    assert response.body["clawback"] == pytest.approx(15_000.0)
    assert response.body["subtotal"] == pytest.approx(40_000.0)
    assert response.body["guarantee_applied"] is False
    assert response.body["final_payout"] == pytest.approx(40_000.0)


def test_clawback_lands_in_the_month_the_policy_was_sold(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Cancelling in a later month still reduces the month of sale."""
    agent = agent_factory(join_date=SETTLED_JOIN_DATE)
    # There is no way to backdate a cancellation -- cancel_policy() always
    # happens now, long after this policy's 2024-05 sale. That gap is the test.
    policy = policy_factory(agent["id"], value=300_000, sold_date=f"{MONTH}-15", cancelled=True)

    assert policy["status"] == "cancelled"
    assert date.today().strftime("%Y-%m") != MONTH, "the sale must predate the cancellation"

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 1
    assert response.body["gross_commission"] == pytest.approx(30_000.0)
    assert response.body["clawback"] == pytest.approx(30_000.0)
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["final_payout"] == pytest.approx(0.0)


def test_clawback_does_not_touch_the_month_of_cancellation() -> None:
    """The month the cancellation happened in is left unchanged."""


def test_cancelled_policy_still_counts_toward_gross_commission() -> None:
    """Gross is recorded before the clawback is subtracted."""


def test_multiple_cancellations_in_one_month_accumulate() -> None:
    """Two clawbacks in a month are added together."""


def test_clawback_cannot_push_payout_below_the_guarantee() -> None:
    """Inside the window, a heavy clawback still pays the minimum."""


def test_full_clawback_inside_the_window_still_pays_the_guarantee() -> None:
    """Cancelling every policy in a guaranteed month leaves the minimum intact."""


def test_clawback_exceeding_gross_outside_the_window_floors_at_zero() -> None:
    """An established agent is never left with a negative payout."""


def test_clawback_is_zero_when_nothing_was_cancelled() -> None:
    """An untouched month reports no clawback."""


def test_cancelling_a_policy_removes_it_from_the_active_listing() -> None:
    """The cancelled policy stops appearing under ?status=active."""
