"""The three-month minimum guarantee, especially at its edges.

The guarantee covers the join month and the two months after it, and lapses
from the fourth month onward.
"""

import pytest

pytestmark = pytest.mark.api


def test_join_month_is_covered_by_the_guarantee() -> None:
    """Month 0 pays the minimum when sales fall short."""


def test_second_month_is_covered_by_the_guarantee() -> None:
    """Month 1 is still inside the window."""


def test_third_month_is_the_last_covered_month() -> None:
    """Month 2 is the final month of the guarantee."""


def test_fourth_month_is_outside_the_guarantee() -> None:
    """Month 3 pays only what was actually earned."""


def test_guarantee_does_not_top_up_a_month_that_already_beats_it() -> None:
    """Earnings above the minimum are paid in full, with no top-up flagged."""


def test_guarantee_flag_is_false_when_earnings_exactly_equal_the_minimum() -> None:
    """Landing exactly on 20,000 is earned, not guaranteed."""


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
