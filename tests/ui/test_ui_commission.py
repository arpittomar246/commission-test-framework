"""The commission page: the calculator, the breakdown, the banner and the chart."""

import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest

from pages.commission_page import CommissionPage

pytestmark = pytest.mark.ui


def test_agent_dropdown_lists_every_agent(
    agent_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The dropdown is populated from the API."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    plain = agent_factory(name=f"{token} Plain")
    awkward = agent_factory(name=f"{token} <b>O'Brien</b> & Co")
    commission_page.reload()

    options = commission_page.testid(CommissionPage.AGENT_SELECT).locator("option")
    values = options.evaluate_all("(nodes) => nodes.map((n) => n.value)")
    labels = commission_page.agent_options()

    assert values[0] == ""
    assert labels[0] == "Select an agent"
    assert commission_page.get_value(CommissionPage.AGENT_SELECT) == ""

    duplicated = [v for v, seen in Counter(values).items() if seen > 1]
    assert not duplicated, f"agents listed more than once: {duplicated}"
    assert all(v.isdigit() for v in values[1:])

    label_for = dict(zip(values, labels))
    for agent in (plain, awkward):
        assert label_for[str(agent["id"])] == agent["name"]
    assert options.locator("b").count() == 0


def test_month_defaults_to_the_local_month_not_the_utc_one(browser, app_config) -> None:
    """At 2 am in India on the 1st, the month picker opens on the new month."""
    context = browser.new_context(base_url=app_config.base_url, timezone_id="Asia/Kolkata")
    try:
        page = context.new_page()
        india = timezone(timedelta(hours=5, minutes=30))
        page.clock.set_fixed_time(datetime(2026, 12, 1, 2, 0, tzinfo=india))

        commission = CommissionPage(page).goto()

        assert commission.get_value(CommissionPage.MONTH_INPUT) == "2026-12"
    finally:
        context.close()


def test_calculate_renders_the_breakdown_card() -> None:
    """Choosing an agent and month and calculating reveals the result card."""


def test_breakdown_shows_every_line_of_the_calculation() -> None:
    """Gross, clawback, subtotal, guarantee and final payout are all present."""


def test_final_payout_is_displayed_prominently() -> None:
    """The final payout renders as the headline figure."""


def test_guarantee_banner_appears_when_the_minimum_is_applied() -> None:
    """A topped-up month shows the guarantee banner."""


def test_guarantee_banner_is_hidden_when_the_minimum_is_not_applied() -> None:
    """A month that beat the minimum shows no banner."""


def test_guarantee_banner_names_the_amount_the_payout_was_raised_to() -> None:
    """The banner reports the final payout figure."""


def test_clawback_is_displayed_as_a_deduction() -> None:
    """The clawback line reads as a subtraction."""


def test_chart_plots_the_last_six_months() -> None:
    """The chart is drawn with six month labels."""


def test_chart_payouts_match_the_history_endpoint() -> None:
    """The plotted values match what the API returned."""


def test_included_policies_table_lists_the_months_policies() -> None:
    """The table shows exactly the policies sold in the selected month."""


def test_included_policies_table_shows_per_policy_commission() -> None:
    """Each listed policy shows 10% of its value."""


def test_empty_state_shows_when_the_agent_sold_nothing_that_month() -> None:
    """A month with no policies shows the empty state."""


def test_agent_preselected_from_the_agents_page_link() -> None:
    """Arriving via an agent's View commission link preselects that agent."""
