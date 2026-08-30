"""The three-month minimum guarantee, especially at its edges.

The guarantee covers the join month and the two months after it, and lapses
from the fourth month onward.
"""

from datetime import date
from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = pytest.mark.api

# Long enough ago that the window has lapsed under any reading of the rule.
SETTLED_JOIN_DATE = "2023-01-10"

JOIN_DATE = "2024-03-10"
JOIN_MONTH = "2024-03"
SECOND_MONTH = "2024-04"
THIRD_MONTH = "2024-05"
FOURTH_MONTH = "2024-06"
MONTH_BEFORE_JOINING = "2024-02"
MINIMUM_GUARANTEE = 20_000.0

# An agent who joins in November is covered through the following January.
NOVEMBER_JOIN_DATE = "2024-11-15"
NOVEMBER_THIRD_MONTH = "2025-01"
NOVEMBER_FOURTH_MONTH = "2025-02"

# Joining on the last day of January: one day of that month, but still month 0.
# Ninety days from this date lands on 30 April, so a day-counting
# implementation would disagree about April.
LAST_DAY_JOIN_DATE = "2024-01-31"
LAST_DAY_JOIN_MONTH = "2024-01"
LAST_DAY_FOURTH_MONTH = "2024-04"


def test_join_month_is_covered_by_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Month 0 pays the minimum when sales fall short."""
    agent = agent_factory(join_date=JOIN_DATE)
    policy_factory(agent["id"], value=50_000, sold_date=f"{JOIN_MONTH}-18")

    response = api_client.get_commission(agent["id"], JOIN_MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(5_000.0)
    assert response.body["clawback"] == pytest.approx(0.0)
    assert response.body["subtotal"] == pytest.approx(5_000.0)
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)


def test_second_month_is_covered_by_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Month 1 is still inside the window."""
    agent = agent_factory(join_date=JOIN_DATE)
    # A strong join month, to prove the guarantee is judged per month rather
    # than against everything earned since joining.
    policy_factory(agent["id"], value=500_000, sold_date=f"{JOIN_MONTH}-20")
    policy_factory(agent["id"], value=80_000, sold_date=f"{SECOND_MONTH}-05")

    response = api_client.get_commission(agent["id"], SECOND_MONTH)

    assert response.status == 200
    assert response.body["month"] == SECOND_MONTH
    assert response.body["policy_count"] == 1
    assert response.body["gross_commission"] == pytest.approx(8_000.0)
    assert response.body["subtotal"] == pytest.approx(8_000.0)
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)


def test_third_month_is_the_last_covered_month(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Month 2 is the final month of the guarantee."""
    agent = agent_factory(join_date=JOIN_DATE)
    # Earns 19,999 -- one rupee short, so the guarantee has to reach for it.
    policy_factory(agent["id"], value=199_990, sold_date=f"{THIRD_MONTH}-27")

    response = api_client.get_commission(agent["id"], THIRD_MONTH)

    assert response.status == 200
    assert response.body["month"] == THIRD_MONTH
    assert response.body["gross_commission"] == pytest.approx(19_999.0)
    assert response.body["subtotal"] == pytest.approx(19_999.0)
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(1.0)


def test_fourth_month_is_outside_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Month 3 pays only what was actually earned."""
    agent = agent_factory(join_date=JOIN_DATE)
    # The same one-rupee shortfall the third month was topped up for; here the
    # window has closed, so the agent keeps 19,999 and nothing reaches for it.
    policy_factory(agent["id"], value=199_990, sold_date=f"{FOURTH_MONTH}-27")

    response = api_client.get_commission(agent["id"], FOURTH_MONTH)

    assert response.status == 200
    assert response.body["month"] == FOURTH_MONTH
    assert response.body["gross_commission"] == pytest.approx(19_999.0)
    assert response.body["subtotal"] == pytest.approx(19_999.0)
    assert response.body["guarantee_applied"] is False
    assert response.body["final_payout"] == pytest.approx(19_999.0)
    assert response.body["final_payout"] < MINIMUM_GUARANTEE
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(0.0)


def test_guarantee_does_not_top_up_a_month_that_already_beats_it(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Earnings above the minimum are paid in full, with no top-up flagged."""
    agent = agent_factory(join_date=JOIN_DATE)
    # Inside the window, but earning 35,000 -- the guarantee has nothing to add.
    policy_factory(agent["id"], value=350_000, sold_date=f"{SECOND_MONTH}-12")

    response = api_client.get_commission(agent["id"], SECOND_MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(35_000.0)
    assert response.body["subtotal"] == pytest.approx(35_000.0)
    assert response.body["guarantee_applied"] is False
    assert response.body["final_payout"] == pytest.approx(35_000.0)
    assert response.body["final_payout"] > MINIMUM_GUARANTEE
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(0.0)


def test_guarantee_flag_is_false_when_earnings_exactly_equal_the_minimum(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Landing exactly on 20,000 is earned, not guaranteed."""
    agent = agent_factory(join_date=JOIN_DATE)
    # Exactly the guarantee, to the rupee: max() returns the same number either
    # way, so only the flag can say whether the guarantee did any work.
    policy_factory(agent["id"], value=200_000, sold_date=f"{SECOND_MONTH}-12")

    response = api_client.get_commission(agent["id"], SECOND_MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(MINIMUM_GUARANTEE)
    assert response.body["subtotal"] == pytest.approx(MINIMUM_GUARANTEE)
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    assert response.body["guarantee_applied"] is False
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(0.0)


def test_zero_sales_inside_the_window_still_pay_the_minimum(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """An agent with no policies at all is paid the guarantee."""
    # No policy_factory here on purpose: the agent has sold nothing, ever.
    agent = agent_factory(join_date=JOIN_DATE)

    response = api_client.get_commission(agent["id"], JOIN_MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 0
    assert response.body["gross_commission"] == pytest.approx(0.0)
    assert response.body["clawback"] == pytest.approx(0.0)
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["guarantee_applied"] is True
    assert response.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    top_up = response.body["final_payout"] - response.body["subtotal"]
    assert top_up == pytest.approx(MINIMUM_GUARANTEE)


def test_months_before_the_join_date_are_not_covered(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """A month earlier than the join date gets no guarantee."""
    # Deliberately the same shape as the zero-sales test above -- an agent with
    # no policies -- so the queried month is the only thing that differs.
    agent = agent_factory(join_date=JOIN_DATE)

    response = api_client.get_commission(agent["id"], MONTH_BEFORE_JOINING)

    assert response.status == 200
    assert response.body["policy_count"] == 0
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["guarantee_applied"] is False
    assert response.body["final_payout"] == pytest.approx(0.0)


def test_guarantee_window_spans_a_year_boundary(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """An agent joining in November is covered through January."""
    agent = agent_factory(join_date=NOVEMBER_JOIN_DATE)
    policy_factory(agent["id"], value=50_000, sold_date=f"{NOVEMBER_THIRD_MONTH}-09")
    policy_factory(agent["id"], value=50_000, sold_date=f"{NOVEMBER_FOURTH_MONTH}-09")

    january = api_client.get_commission(agent["id"], NOVEMBER_THIRD_MONTH)
    february = api_client.get_commission(agent["id"], NOVEMBER_FOURTH_MONTH)

    # January is month 2 -- the last covered month, on the far side of the year.
    assert january.body["subtotal"] == pytest.approx(5_000.0)
    assert january.body["guarantee_applied"] is True
    assert january.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)

    # February is month 3, so the window has closed and the earnings stand.
    assert february.body["subtotal"] == pytest.approx(5_000.0)
    assert february.body["guarantee_applied"] is False
    assert february.body["final_payout"] == pytest.approx(5_000.0)


def test_guarantee_window_is_measured_in_calendar_months_not_days(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Joining on the last day of a month still spends that whole month in the window."""
    agent = agent_factory(join_date=LAST_DAY_JOIN_DATE)
    policy_factory(agent["id"], value=50_000, sold_date=f"{LAST_DAY_JOIN_MONTH}-31")
    policy_factory(agent["id"], value=50_000, sold_date=f"{LAST_DAY_FOURTH_MONTH}-15")

    january = api_client.get_commission(agent["id"], LAST_DAY_JOIN_MONTH)
    april = api_client.get_commission(agent["id"], LAST_DAY_FOURTH_MONTH)

    # One day on the books, but January is month 0 and covered in full.
    assert january.body["subtotal"] == pytest.approx(5_000.0)
    assert january.body["guarantee_applied"] is True
    assert january.body["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)

    # April is month 3 and uncovered, even though it is inside 90 days of joining.
    assert april.body["subtotal"] == pytest.approx(5_000.0)
    assert april.body["guarantee_applied"] is False
    assert april.body["final_payout"] == pytest.approx(5_000.0)


def test_guarantee_flag_reported_on_the_agent_record_matches_the_calculation(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """The agent's guarantee_active field agrees with the current month's breakdown."""
    # The only test here anchored to today: guarantee_active on the agent record
    # is always reported for the current month, so the query has to follow it.
    this_month = date.today().strftime("%Y-%m")
    fresh = agent_factory(join_date=date.today().isoformat())
    settled = agent_factory(join_date=SETTLED_JOIN_DATE)

    fresh_record = api_client.get_agent(fresh["id"]).body
    settled_record = api_client.get_agent(settled["id"]).body
    fresh_breakdown = api_client.get_commission(fresh["id"], this_month).body
    settled_breakdown = api_client.get_commission(settled["id"], this_month).body

    assert fresh_record["guarantee_active"] is True
    assert fresh_record["months_active"] == 0
    assert settled_record["guarantee_active"] is False

    # Neither has sold anything, so the record's flag alone decides the payout.
    assert fresh_breakdown["guarantee_applied"] is True
    assert fresh_breakdown["final_payout"] == pytest.approx(MINIMUM_GUARANTEE)
    assert settled_breakdown["guarantee_applied"] is False
    assert settled_breakdown["final_payout"] == pytest.approx(0.0)

    # The invariant tying the two endpoints together: a month can only have the
    # guarantee applied while the agent record says the window is open.
    for record, breakdown in ((fresh_record, fresh_breakdown), (settled_record, settled_breakdown)):
        if breakdown["guarantee_applied"]:
            assert record["guarantee_active"] is True
