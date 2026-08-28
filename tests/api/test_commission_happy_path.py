"""Commission calculation on the ordinary path.

An agent with straightforward sales and no cancellations: 10% of every policy
sold in the month, no clawback, no guarantee top-up.

Every agent here joins in ``SETTLED_JOIN`` and every policy is sold in
``MONTH`` -- far enough apart that the minimum guarantee has long lapsed, so
these tests see the raw 10% and nothing else.  The guarantee gets its own file.
"""

from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = [pytest.mark.api, pytest.mark.smoke]

SETTLED_JOIN = "2023-01-10"
MONTH = "2024-05"
RATE = 0.10


def test_commission_is_ten_percent_of_a_single_policy(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """One policy in the month pays 10% of its value."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    policy_factory(agent["id"], value=250_000, sold_date=f"{MONTH}-08")

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(25_000.0)
    assert response.body["clawback"] == pytest.approx(0.0)
    assert response.body["subtotal"] == pytest.approx(25_000.0)
    assert response.body["final_payout"] == pytest.approx(25_000.0)
    assert response.body["guarantee_applied"] is False


def test_commission_sums_every_policy_in_the_month(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Several policies in one month add up."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    values = [100_000, 250_000, 60_000]
    for day, value in enumerate(values, start=3):
        policy_factory(agent["id"], value=value, sold_date=f"{MONTH}-{day:02d}")

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["gross_commission"] == pytest.approx(sum(values) * RATE)
    assert response.body["final_payout"] == pytest.approx(41_000.0)
    assert response.body["policy_count"] == len(values)


def test_policies_from_other_months_are_excluded(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Only policies sold inside the requested month count."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    policy_factory(agent["id"], value=500_000, sold_date="2024-04-28")
    policy_factory(agent["id"], value=300_000, sold_date=f"{MONTH}-15")
    policy_factory(agent["id"], value=700_000, sold_date="2024-06-01")

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 1
    assert response.body["gross_commission"] == pytest.approx(30_000.0)
    assert response.body["final_payout"] == pytest.approx(30_000.0)


def test_month_with_no_policies_pays_nothing_outside_the_guarantee(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """An established agent who sold nothing is paid nothing."""
    agent = agent_factory(join_date=SETTLED_JOIN)

    response = api_client.get_commission(agent["id"], MONTH)

    assert response.status == 200
    assert response.body["policy_count"] == 0
    assert response.body["gross_commission"] == pytest.approx(0.0)
    assert response.body["subtotal"] == pytest.approx(0.0)
    assert response.body["final_payout"] == pytest.approx(0.0)
    assert response.body["guarantee_applied"] is False


def test_breakdown_fields_are_internally_consistent(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Subtotal equals gross minus clawback, and the final payout follows from it."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    policy_factory(agent["id"], value=400_000, sold_date=f"{MONTH}-05")
    policy_factory(agent["id"], value=150_000, sold_date=f"{MONTH}-09", cancelled=True)

    body = api_client.get_commission(agent["id"], MONTH).body

    assert body["subtotal"] == pytest.approx(body["gross_commission"] - body["clawback"])
    assert body["final_payout"] == pytest.approx(max(body["subtotal"], 0.0))
    assert body["guarantee_applied"] is (body["final_payout"] > body["subtotal"])
    assert body["agent_id"] == agent["id"]
    assert body["month"] == MONTH


def test_policy_count_matches_the_policies_sold_that_month(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """The reported policy_count counts the month's policies, cancelled ones included."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    policy_factory(agent["id"], value=100_000, sold_date=f"{MONTH}-02")
    policy_factory(agent["id"], value=100_000, sold_date=f"{MONTH}-11")
    policy_factory(agent["id"], value=100_000, sold_date=f"{MONTH}-20", cancelled=True)

    body = api_client.get_commission(agent["id"], MONTH).body

    assert body["policy_count"] == 3
    assert body["clawback"] == pytest.approx(10_000.0)


def test_fractional_policy_values_round_to_two_decimals(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Odd values do not leak floating-point noise into the payout."""
    agent = agent_factory(join_date=SETTLED_JOIN)
    for day in (4, 14, 24):
        policy_factory(agent["id"], value=33_333.33, sold_date=f"{MONTH}-{day:02d}")

    body = api_client.get_commission(agent["id"], MONTH).body

    assert body["gross_commission"] == 9_999.99
    for field in ("gross_commission", "clawback", "subtotal", "final_payout"):
        assert round(body[field], 2) == body[field], f"{field} carries more than 2 decimals"


def test_commission_is_isolated_per_agent(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """One agent's sales never show up in another agent's payout."""
    seller = agent_factory(name="Seller", join_date=SETTLED_JOIN)
    idler = agent_factory(name="Idler", join_date=SETTLED_JOIN)
    policy_factory(seller["id"], value=800_000, sold_date=f"{MONTH}-18")

    sold = api_client.get_commission(seller["id"], MONTH).body
    quiet = api_client.get_commission(idler["id"], MONTH).body

    assert sold["final_payout"] == pytest.approx(80_000.0)
    assert sold["policy_count"] == 1
    assert quiet["final_payout"] == pytest.approx(0.0)
    assert quiet["policy_count"] == 0
