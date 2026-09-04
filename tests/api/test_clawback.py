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

# For the rule-4 tests: an agent whose GUARANTEE_MONTH is month 1, still well
# inside the three-month window.
GUARANTEE_JOIN_DATE = "2024-03-10"
GUARANTEE_MONTH = "2024-04"
MINIMUM_GUARANTEE = 20_000.0


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


def test_clawback_does_not_touch_the_month_of_cancellation(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """The month the cancellation happened in is left unchanged."""
    today = date.today()
    this_month = today.strftime("%Y-%m")
    agent = agent_factory(join_date=SETTLED_JOIN_DATE)

    # Cancelled now, but sold back in 2024-05 -- the reversal belongs there.
    policy_factory(agent["id"], value=300_000, sold_date=f"{MONTH}-15", cancelled=True)
    # Sold this month and left alone, so the current month has earnings of its
    # own that a misplaced clawback would visibly eat into.
    policy_factory(agent["id"], value=250_000, sold_date=today.isoformat())

    response = api_client.get_commission(agent["id"], this_month)

    assert response.status == 200
    assert response.body["month"] == this_month
    assert response.body["policy_count"] == 1
    assert response.body["clawback"] == pytest.approx(0.0)
    assert response.body["gross_commission"] == pytest.approx(25_000.0)
    assert response.body["subtotal"] == pytest.approx(25_000.0)
    assert response.body["final_payout"] == pytest.approx(25_000.0)


def test_cancelled_policy_still_counts_toward_gross_commission(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Gross is recorded before the clawback is subtracted."""
    # Two agents selling exactly the same book; only one of them cancels
    # anything. Gross has to come out identical, because gross describes what
    # was sold -- the cancellation is a separate line beneath it.
    sales = [200_000, 300_000, 100_000]
    cancelling = agent_factory(name="Cancels One", join_date=SETTLED_JOIN_DATE)
    keeping = agent_factory(name="Cancels Nothing", join_date=SETTLED_JOIN_DATE)

    for day, value in enumerate(sales, start=7):
        policy_factory(
            cancelling["id"], value=value, sold_date=f"{MONTH}-{day:02d}",
            cancelled=(value == 300_000),
        )
        policy_factory(keeping["id"], value=value, sold_date=f"{MONTH}-{day:02d}")

    cancelled_book = api_client.get_commission(cancelling["id"], MONTH).body
    intact_book = api_client.get_commission(keeping["id"], MONTH).body

    # The line that survives a cancellation untouched.
    assert cancelled_book["gross_commission"] == pytest.approx(60_000.0)
    assert cancelled_book["gross_commission"] == pytest.approx(intact_book["gross_commission"])
    assert cancelled_book["policy_count"] == intact_book["policy_count"] == len(sales)

    # The lines that do not.
    assert cancelled_book["clawback"] == pytest.approx(30_000.0)
    assert intact_book["clawback"] == pytest.approx(0.0)
    assert cancelled_book["subtotal"] == pytest.approx(30_000.0)
    assert intact_book["subtotal"] == pytest.approx(60_000.0)


def test_multiple_cancellations_in_one_month_accumulate(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Two clawbacks in a month are added together."""
    agent = agent_factory(join_date=SETTLED_JOIN_DATE)
    # Two different cancelled values, so a sum is distinguishable from either
    # one alone -- last-wins and max-wins both land on a single value.
    cancelled_values = [90_000, 250_000]
    policy_factory(agent["id"], value=400_000, sold_date=f"{MONTH}-04")
    for day, value in zip((12, 21), cancelled_values):
        policy_factory(agent["id"], value=value, sold_date=f"{MONTH}-{day}", cancelled=True)

    response = api_client.get_commission(agent["id"], MONTH)
    reversals = [round(value * 0.10, 2) for value in cancelled_values]

    assert response.status == 200
    assert response.body["policy_count"] == 3
    assert response.body["gross_commission"] == pytest.approx(74_000.0)
    assert response.body["clawback"] == pytest.approx(sum(reversals))
    assert response.body["clawback"] == pytest.approx(34_000.0)
    # Neither reversal alone, and not the larger of the two.
    assert response.body["clawback"] > max(reversals)
    assert response.body["subtotal"] == pytest.approx(40_000.0)
    assert response.body["final_payout"] == pytest.approx(40_000.0)


def test_clawback_cannot_push_payout_below_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Inside the window, a heavy clawback still pays the minimum."""
    agent = agent_factory(join_date=GUARANTEE_JOIN_DATE)
    # Gross clears the floor comfortably, but the surviving policy alone does
    # not: the drop below the minimum is caused by the clawback and nothing else.
    policy_factory(agent["id"], value=150_000, sold_date=f"{GUARANTEE_MONTH}-06")
    policy_factory(agent["id"], value=250_000, sold_date=f"{GUARANTEE_MONTH}-19", cancelled=True)

    response = api_client.get_commission(agent["id"], GUARANTEE_MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(40_000.0)
    assert response.body["gross_commission"] > MINIMUM_GUARANTEE
    assert response.body["clawback"] == pytest.approx(25_000.0)

    # The clawback is applied in full -- it is the payout that is floored, not
    # the clawback that is trimmed to fit.
    assert response.body["subtotal"] == pytest.approx(15_000.0)
    assert response.body["subtotal"] < MINIMUM_GUARANTEE
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(5_000.0)


def test_full_clawback_inside_the_window_still_pays_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Cancelling every policy in a guaranteed month leaves the minimum intact."""
    agent = agent_factory(join_date=GUARANTEE_JOIN_DATE)
    # Nothing survives, so the subtotal is exactly zero and the guarantee is
    # carrying the whole payout -- the heaviest case the floor has to absorb.
    for day, value in ((8, 350_000), (23, 150_000)):
        policy_factory(
            agent["id"], value=value, sold_date=f"{GUARANTEE_MONTH}-{day:02d}", cancelled=True
        )

    response = api_client.get_commission(agent["id"], GUARANTEE_MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 2
    assert response.body["gross_commission"] == pytest.approx(50_000.0)
    assert response.body["clawback"] == pytest.approx(50_000.0)
    # Everything earned was reversed, so these two lines have to agree.
    assert response.body["clawback"] == pytest.approx(response.body["gross_commission"])
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(MINIMUM_GUARANTEE)


def test_clawback_exceeding_gross_outside_the_window_floors_at_zero(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """An established agent is never left with a negative payout."""
    # The same fully reversed month as the test above, but settled: with no
    # guarantee to catch it, the payout stops at zero rather than at 20,000.
    agent = agent_factory(join_date=SETTLED_JOIN_DATE)
    for day, value in ((8, 350_000), (23, 150_000)):
        policy_factory(
            agent["id"], value=value, sold_date=f"{MONTH}-{day:02d}", cancelled=True
        )

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(50_000.0)
    assert response.body["clawback"] == pytest.approx(50_000.0)
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["guarantee_applied"] is False
    assert response.body["final_payout"] == pytest.approx(0.0)

    # The decision the README records: the agent is never asked to pay money
    # back, so neither line may go negative however heavy the reversal.
    assert response.body["subtotal"] >= 0.0
    assert response.body["final_payout"] >= 0.0


def test_clawback_is_zero_when_nothing_was_cancelled() -> None:
    """An untouched month reports no clawback."""


def test_cancelling_a_policy_removes_it_from_the_active_listing() -> None:
    """The cancelled policy stops appearing under ?status=active."""
