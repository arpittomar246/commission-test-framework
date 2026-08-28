"""Commission rules for insurance agents.

Pure functions only -- nothing here touches the database, the network or the
clock.  Every input is passed in explicitly so the rules can be exercised in
isolation.

The rules, in the order they are applied:

1. Commission is ``COMMISSION_RATE`` (10%) of a policy's value.
2. For the first ``GUARANTEE_MONTHS`` (3) calendar months from an agent's
   ``join_date`` the monthly payout is at least ``MINIMUM_GUARANTEE``
   (20,000), even when the agent sold nothing at all.
3. Cancelling a policy claws its commission back from the month the policy was
   *sold*, never the month it was cancelled.
4. The clawback may never drag the payout below the minimum guarantee while the
   guarantee is still in force.

Outside the guarantee window a clawback-heavy month floors at zero: an agent is
never asked to pay money back through this calculation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

COMMISSION_RATE = 0.10
MINIMUM_GUARANTEE = 20_000.0
GUARANTEE_MONTHS = 3

_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class InvalidMonthError(ValueError):
    """Raised when a month string is not a valid ``YYYY-MM`` value."""


@dataclass(frozen=True)
class PolicyRecord:
    """The slice of a policy the commission rules actually care about."""

    id: int
    value: float
    sold_date: date
    cancelled: bool


@dataclass(frozen=True)
class CommissionBreakdown:
    """The month's payout, broken into the steps that produced it."""

    month: str
    gross_commission: float
    clawback: float
    subtotal: float
    guarantee_applied: bool
    final_payout: float
    policy_count: int


def parse_month(month: str) -> tuple[int, int]:
    """Split a ``YYYY-MM`` string into a (year, month) pair."""
    if not isinstance(month, str) or not _MONTH_PATTERN.match(month):
        raise InvalidMonthError(f"month must look like YYYY-MM, got {month!r}")
    year, mon = month.split("-")
    return int(year), int(mon)


def month_key(day: date) -> str:
    """Render a date as the ``YYYY-MM`` bucket it belongs to."""
    return f"{day.year:04d}-{day.month:02d}"


def months_since_join(join_date: date, month: str) -> int:
    """Count whole calendar months between an agent's join month and ``month``.

    The join month itself is month 0, so an agent who joined in March is two
    months in by May.  A month before the agent joined comes back negative.
    """
    year, mon = parse_month(month)
    return (year - join_date.year) * 12 + (mon - join_date.month)


def months_active(join_date: date, today: date) -> int:
    """Calendar months the agent has been on the books as of ``today``."""
    return months_since_join(join_date, month_key(today))


def is_guarantee_active(join_date: date, month: str) -> bool:
    """Whether the minimum guarantee covers ``month`` for this agent."""
    return 0 <= months_since_join(join_date, month) < GUARANTEE_MONTHS


def commission_for(value: float) -> float:
    """Commission earned on a single policy value."""
    return round(float(value) * COMMISSION_RATE, 2)


def policies_sold_in(policies: list[PolicyRecord], month: str) -> list[PolicyRecord]:
    """Every policy whose *sold* date falls inside ``month``."""
    parse_month(month)
    return [p for p in policies if month_key(p.sold_date) == month]


def calculate_commission(
    join_date: date,
    month: str,
    policies: list[PolicyRecord],
) -> CommissionBreakdown:
    """Work out one agent's payout for one month.

    ``policies`` may be the agent's whole book -- anything sold outside
    ``month`` is ignored, and a cancelled policy is clawed back from the month
    it was sold in rather than the month it was cancelled.
    """
    in_month = policies_sold_in(policies, month)

    gross = round(float(sum(commission_for(p.value) for p in in_month)), 2)
    clawback = round(float(sum(commission_for(p.value) for p in in_month if p.cancelled)), 2)
    subtotal = round(gross - clawback, 2)

    if is_guarantee_active(join_date, month):
        final_payout = max(subtotal, MINIMUM_GUARANTEE)
    else:
        final_payout = max(subtotal, 0.0)

    return CommissionBreakdown(
        month=month,
        gross_commission=gross,
        clawback=clawback,
        subtotal=subtotal,
        guarantee_applied=final_payout > subtotal,
        final_payout=round(final_payout, 2),
        policy_count=len(in_month),
    )


def recent_months(month: str, count: int = 6) -> list[str]:
    """The ``count`` months ending at ``month``, oldest first."""
    year, mon = parse_month(month)
    months: list[str] = []
    for offset in range(count - 1, -1, -1):
        total = year * 12 + (mon - 1) - offset
        months.append(f"{total // 12:04d}-{total % 12 + 1:02d}")
    return months
