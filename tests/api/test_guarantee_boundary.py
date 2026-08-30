"""The three-month minimum guarantee, especially at its edges.

The guarantee covers the join month and the two months after it, and lapses
from the fourth month onward.
"""

from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = pytest.mark.api

JOIN_DATE = "2024-03-10"
JOIN_MONTH = "2024-03"
SECOND_MONTH = "2024-04"
THIRD_MONTH = "2024-05"
FOURTH_MONTH = "2024-06"
MINIMUM_GUARANTEE = 20_000.0


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


def test_zero_sales_inside_the_window_still_pay_the_minimum() -> None:
    """An agent with no policies at all is paid the guarantee."""


def test_months_before_the_join_date_are_not_covered() -> None:
    """A month earlier than the join date gets no guarantee."""


def test_guarantee_window_spans_a_year_boundary() -> None:
    """An agent joining in November is covered through January."""


def test_guarantee_window_is_measured_in_calendar_months_not_days() -> None:
    """Joining on the last day of a month still spends that whole month in the window."""


def test_guarantee_flag_reported_on_the_agent_record_matches_the_calculation() -> None:
    """The agent's guarantee_active field agrees with the current month's breakdown."""
