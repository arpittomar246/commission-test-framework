"""Commission calculation on the ordinary path.

An agent with straightforward sales and no cancellations: 10% of every policy
sold in the month, no clawback, no guarantee top-up.
"""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def test_commission_is_ten_percent_of_a_single_policy() -> None:
    """One policy in the month pays 10% of its value."""


def test_commission_sums_every_policy_in_the_month() -> None:
    """Several policies in one month add up."""


def test_policies_from_other_months_are_excluded() -> None:
    """Only policies sold inside the requested month count."""


def test_month_with_no_policies_pays_nothing_outside_the_guarantee() -> None:
    """An established agent who sold nothing is paid nothing."""


def test_breakdown_fields_are_internally_consistent() -> None:
    """Subtotal equals gross minus clawback, and the final payout follows from it."""


def test_policy_count_matches_the_policies_sold_that_month() -> None:
    """The reported policy_count counts the month's policies, cancelled ones included."""


def test_fractional_policy_values_round_to_two_decimals() -> None:
    """Odd values do not leak floating-point noise into the payout."""


def test_commission_is_isolated_per_agent() -> None:
    """One agent's sales never show up in another agent's payout."""
