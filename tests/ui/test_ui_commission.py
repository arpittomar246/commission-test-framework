"""The commission page: the calculator, the breakdown, the banner and the chart."""

import pytest

pytestmark = pytest.mark.ui


def test_agent_dropdown_lists_every_agent() -> None:
    """The dropdown is populated from the API."""


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
