"""Clawbacks when a policy is cancelled.

A cancellation reverses the policy's commission against the month the policy
was *sold*, never the month it was cancelled -- and it can never push a payout
below the minimum guarantee while that guarantee is in force.
"""

import pytest

pytestmark = pytest.mark.api


def test_cancelling_a_policy_reverses_its_commission() -> None:
    """The clawback equals 10% of the cancelled policy's value."""


def test_clawback_lands_in_the_month_the_policy_was_sold() -> None:
    """Cancelling in a later month still reduces the month of sale."""


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
