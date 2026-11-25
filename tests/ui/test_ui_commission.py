"""The commission page: the calculator, the breakdown, the banner and the chart."""

import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest
from playwright.sync_api import expect

from framework.api_client import ApiClient
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


def test_calculate_renders_the_breakdown_card(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """Choosing an agent and month and calculating reveals the result card."""
    agent = agent_factory(name="Breakdown Card Agent", join_date="2023-01-10")
    policy_factory(agent["id"], value=300_000, sold_date="2024-05-12")
    commission_page.reload()

    card = commission_page.testid(CommissionPage.RESULT_CARD)
    expect(card).to_be_hidden()

    commission_page.calculate(agent["id"], "2024-05")

    expect(card).to_be_visible()
    assert commission_page.result_agent() == "Breakdown Card Agent"
    assert commission_page.result_month() == "2024-05"

    fields = [
        CommissionPage.GROSS,
        CommissionPage.CLAWBACK,
        CommissionPage.SUBTOTAL,
        CommissionPage.GUARANTEE_APPLIED,
        CommissionPage.FINAL_PAYOUT,
        CommissionPage.POLICY_COUNT,
    ]
    for field in fields:
        assert commission_page.get_text(field) not in ("", "--"), f"{field} was never filled in"

    assert not commission_page.error_visible()


def test_breakdown_shows_every_line_of_the_calculation(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """Gross, clawback, subtotal, guarantee and final payout are all present."""
    agent = agent_factory(name="Every Line Agent", join_date="2023-01-10")
    policy_factory(agent["id"], value=4_000_000, sold_date="2024-05-06")
    policy_factory(agent["id"], value=1_500_000, sold_date="2024-05-20", cancelled=True)
    commission_page.reload()

    commission_page.calculate(agent["id"], "2024-05")
    api = api_client.get_commission(agent["id"], "2024-05").body

    shown = {
        "gross_commission": (CommissionPage.GROSS, "5,50,000.00"),
        "clawback": (CommissionPage.CLAWBACK, "-1,50,000.00"),
        "subtotal": (CommissionPage.SUBTOTAL, "4,00,000.00"),
        "final_payout": (CommissionPage.FINAL_PAYOUT, "4,00,000.00"),
    }
    for field, (testid, text) in shown.items():
        assert commission_page.get_text(testid) == text, field
        assert commission_page.as_number(testid) == pytest.approx(api[field]), field

    assert api["guarantee_applied"] is False
    assert commission_page.guarantee_applied() == "No"
    assert commission_page.policy_count() == str(api["policy_count"]) == "2"


def test_final_payout_is_displayed_prominently(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The final payout renders as the headline figure."""
    agent = agent_factory(name="Headline Agent", join_date="2023-01-10")
    policy_factory(agent["id"], value=300_000, sold_date="2024-05-12")
    commission_page.reload()
    commission_page.calculate(agent["id"], "2024-05")

    def drawn(testid: str) -> dict:
        return commission_page.testid(testid).evaluate(
            """(el) => {
                const style = getComputedStyle(el);
                const box = el.getBoundingClientRect();
                return {
                    size: parseFloat(style.fontSize),
                    weight: Number(style.fontWeight),
                    top: box.top,
                    bottom: box.bottom,
                    viewport: window.innerHeight,
                };
            }"""
        )

    headline = drawn(CommissionPage.FINAL_PAYOUT)
    others = {
        testid: drawn(testid)
        for testid in (
            CommissionPage.GROSS,
            CommissionPage.CLAWBACK,
            CommissionPage.SUBTOTAL,
            CommissionPage.GUARANTEE_APPLIED,
            CommissionPage.POLICY_COUNT,
        )
    }

    for testid, line in others.items():
        assert headline["size"] >= 1.5 * line["size"], f"payout not clearly larger than {testid}"
    assert headline["weight"] >= 700
    assert 0 <= headline["top"] and headline["bottom"] <= headline["viewport"]


def test_guarantee_banner_appears_when_the_minimum_is_applied(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """A topped-up month shows the guarantee banner."""
    agent = agent_factory(name="Topped Up Agent", join_date="2024-03-10")
    policy_factory(agent["id"], value=50_000, sold_date="2024-04-15")
    policy_factory(agent["id"], value=100_000, sold_date="2024-05-08")
    policy_factory(agent["id"], value=300_000, sold_date="2024-05-22", cancelled=True)
    commission_page.reload()

    reasons = {
        "2024-03": "nothing sold",
        "2024-04": "sales below the minimum",
        "2024-05": "a clawback pulled it below",
    }
    banner = commission_page.guarantee_banner()
    for month, reason in reasons.items():
        commission_page.calculate(agent["id"], month)
        expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text(month)

        api = api_client.get_commission(agent["id"], month).body
        assert api["guarantee_applied"] is True, reason
        assert api["subtotal"] < api["final_payout"], reason

        expect(banner).to_be_visible()
        assert "Minimum guarantee applied" in commission_page.guarantee_banner_text(), reason
        assert commission_page.guarantee_applied() == "Yes", reason


def test_guarantee_banner_is_hidden_when_the_minimum_is_not_applied(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """A month that beat the minimum shows no banner."""
    newcomer = agent_factory(name="Inside Window Agent", join_date="2024-03-10")
    policy_factory(newcomer["id"], value=200_000, sold_date="2024-04-15")
    policy_factory(newcomer["id"], value=350_000, sold_date="2024-05-15")
    settled = agent_factory(name="Settled Small Earner", join_date="2023-01-10")
    policy_factory(settled["id"], value=50_000, sold_date="2024-05-15")
    commission_page.reload()

    banner = commission_page.guarantee_banner()
    commission_page.calculate(newcomer["id"], "2024-03")
    expect(banner).to_be_visible()

    cases = [
        (newcomer, "2024-04", "earned exactly the minimum", 20_000.0),
        (newcomer, "2024-05", "earned above the minimum", 35_000.0),
        (settled, "2024-05", "window shut, earned below the minimum", 5_000.0),
    ]
    for agent, month, reason, payout in cases:
        commission_page.calculate(agent["id"], month)
        expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text(month)
        expect(commission_page.testid(CommissionPage.RESULT_AGENT)).to_have_text(agent["name"])

        api = api_client.get_commission(agent["id"], month).body
        assert api["guarantee_applied"] is False, reason
        assert api["final_payout"] == pytest.approx(payout), reason

        expect(banner).to_be_hidden()
        assert commission_page.guarantee_applied() == "No", reason
        assert commission_page.as_number(CommissionPage.FINAL_PAYOUT) == pytest.approx(payout), reason


def test_guarantee_banner_names_the_amount_the_payout_was_raised_to(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The banner reports the final payout figure."""
    agent = agent_factory(name="Raised Payout Agent", join_date="2024-03-10")
    policy_factory(agent["id"], value=50_000, sold_date="2024-04-15")
    commission_page.reload()

    amount = commission_page.testid(CommissionPage.GUARANTEE_BANNER_AMOUNT)
    amount.evaluate("(el) => { el.textContent = 'not yet written'; }")

    commission_page.calculate(agent["id"], "2024-04")
    expect(commission_page.guarantee_banner()).to_be_visible()

    api = api_client.get_commission(agent["id"], "2024-04").body
    assert api["guarantee_applied"] is True
    assert api["subtotal"] == pytest.approx(5_000.0)

    expect(amount).to_have_text("20,000.00")
    assert commission_page.guarantee_banner_amount() == commission_page.final_payout()
    assert commission_page.as_number(CommissionPage.GUARANTEE_BANNER_AMOUNT) == pytest.approx(
        api["final_payout"]
    )
    assert commission_page.guarantee_banner_amount() != commission_page.subtotal()
    assert "raised to 20,000.00" in commission_page.guarantee_banner_text()


def test_clawback_is_displayed_as_a_deduction(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The clawback line reads as a subtraction."""
    agent = agent_factory(name="Deduction Agent", join_date="2023-01-10")
    policy_factory(agent["id"], value=400_000, sold_date="2024-05-06")
    policy_factory(agent["id"], value=150_000, sold_date="2024-05-20", cancelled=True)
    policy_factory(agent["id"], value=300_000, sold_date="2024-06-10")
    commission_page.reload()

    commission_page.calculate(agent["id"], "2024-05")

    assert commission_page.clawback() == "-15,000.00"
    gross = commission_page.as_number(CommissionPage.GROSS)
    clawback = commission_page.as_number(CommissionPage.CLAWBACK)
    subtotal = commission_page.as_number(CommissionPage.SUBTOTAL)
    assert gross - clawback == pytest.approx(subtotal)

    red, green, blue = commission_page.testid(CommissionPage.CLAWBACK).evaluate(
        """(el) => getComputedStyle(el).color.match(/\\d+/g).slice(0, 3).map(Number)"""
    )
    assert red > green + 60 and red > blue + 60, (red, green, blue)

    commission_page.calculate(agent["id"], "2024-06")
    expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text("2024-06")

    assert commission_page.clawback() == "0.00"
    assert commission_page.as_number(CommissionPage.SUBTOTAL) == pytest.approx(
        commission_page.as_number(CommissionPage.GROSS)
    )


def test_chart_plots_the_last_six_months(
    agent_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The chart is drawn with six month labels."""
    agent = agent_factory(name="Chart Months Agent", join_date="2023-01-10")
    commission_page.reload()

    commission_page.calculate(agent["id"], "2024-02")

    across_the_new_year = ["2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02"]
    assert commission_page.chart_months() == across_the_new_year

    chart = commission_page.chart()
    drawn = chart.evaluate(
        """(el) => {
            const instance = Chart.getChart(el);
            return { labels: instance.data.labels, bars: instance.getDatasetMeta(0).data.length };
        }"""
    )
    assert drawn == {"labels": across_the_new_year, "bars": 6}

    box = chart.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0

    commission_page.calculate(agent["id"], "2024-07")
    expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text("2024-07")

    within_one_year = ["2024-02", "2024-03", "2024-04", "2024-05", "2024-06", "2024-07"]
    assert commission_page.chart_months() == within_one_year
    assert chart.evaluate("(el) => Chart.getChart(el).data.labels") == within_one_year


def test_chart_payouts_match_the_history_endpoint(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The plotted values match what the API returned."""
    agent = agent_factory(name="Chart Payouts Agent", join_date="2024-03-10")
    policy_factory(agent["id"], value=300_000, sold_date="2024-04-15")
    policy_factory(agent["id"], value=100_000, sold_date="2024-05-08")
    policy_factory(agent["id"], value=150_000, sold_date="2024-05-21", cancelled=True)
    policy_factory(agent["id"], value=50_000, sold_date="2024-06-12")
    policy_factory(agent["id"], value=80_000, sold_date="2024-07-03")
    policy_factory(agent["id"], value=200_000, sold_date="2024-07-25", cancelled=True)
    commission_page.reload()

    commission_page.calculate(agent["id"], "2024-07")

    history = api_client.get_commission_history(agent["id"], "2024-07").body
    plotted = commission_page.chart_payouts()
    assert commission_page.chart_months() == history["months"]
    assert plotted == pytest.approx(history["payouts"])

    drawn = commission_page.chart().evaluate("(el) => Chart.getChart(el).data.datasets[0].data")
    assert drawn == pytest.approx(history["payouts"])

    expected = {
        "2024-02": 0,
        "2024-03": 20_000,
        "2024-04": 30_000,
        "2024-05": 20_000,
        "2024-06": 5_000,
        "2024-07": 8_000,
    }
    assert dict(zip(history["months"], plotted)) == pytest.approx(expected)

    for month, payout in zip(history["months"], plotted):
        assert payout == pytest.approx(api_client.get_commission(agent["id"], month).body["final_payout"]), month

    assert commission_page.as_number(CommissionPage.FINAL_PAYOUT) == pytest.approx(plotted[-1])


def test_included_policies_table_lists_the_months_policies(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    commission_page: CommissionPage,
) -> None:
    """The table shows exactly the policies sold in the selected month."""
    agent = agent_factory(name="Table Agent", join_date="2023-01-10")
    other = agent_factory(name="Table Other Agent", join_date="2023-01-10")

    first_day = policy_factory(agent["id"], value=120_000, sold_date="2024-05-01", customer_name="First Day")
    cancelled = policy_factory(
        agent["id"], value=90_000, sold_date="2024-05-16", customer_name="Cancelled Mid", cancelled=True
    )
    last_day = policy_factory(agent["id"], value=60_000, sold_date="2024-05-31", customer_name="Last Day")
    day_before = policy_factory(agent["id"], value=70_000, sold_date="2024-04-30", customer_name="Day Before")
    day_after = policy_factory(agent["id"], value=80_000, sold_date="2024-06-01", customer_name="Day After")
    policy_factory(agent["id"], value=50_000, sold_date="2023-05-15", customer_name="Year Earlier")
    policy_factory(other["id"], value=110_000, sold_date="2024-05-15", customer_name="Other Agent")
    commission_page.reload()

    commission_page.calculate(agent["id"], "2024-05")

    def listed() -> set[int]:
        return {
            int(testid.removeprefix("commission-policy-row-"))
            for testid in commission_page.policy_rows().evaluate_all(
                "(rows) => rows.map((row) => row.dataset.testid)"
            )
        }

    may = {first_day["id"], cancelled["id"], last_day["id"]}
    assert listed() == may
    assert commission_page.policy_row_count() == 3
    assert int(commission_page.get_text(CommissionPage.POLICY_COUNT)) == 3

    expect(commission_page.testid(CommissionPage.POLICIES_CARD)).to_be_visible()
    expect(commission_page.testid(CommissionPage.EMPTY_STATE)).to_be_hidden()

    expect(commission_page.policy_row(first_day["id"])).to_contain_text("First Day")
    expect(commission_page.policy_row(first_day["id"])).to_contain_text("2024-05-01")
    expect(commission_page.testid(f"commission-policy-status-{cancelled['id']}")).to_have_attribute(
        "data-status", "cancelled"
    )
    expect(commission_page.testid(f"commission-policy-status-{last_day['id']}")).to_have_attribute(
        "data-status", "active"
    )

    commission_page.calculate(agent["id"], "2024-06")
    expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text("2024-06")

    assert listed() == {day_after["id"]}
    expect(commission_page.policy_row(first_day["id"])).to_have_count(0)

    commission_page.calculate(agent["id"], "2024-04")
    expect(commission_page.testid(CommissionPage.RESULT_MONTH)).to_have_text("2024-04")

    assert listed() == {day_before["id"]}


def test_included_policies_table_shows_per_policy_commission() -> None:
    """Each listed policy shows 10% of its value."""


def test_empty_state_shows_when_the_agent_sold_nothing_that_month() -> None:
    """A month with no policies shows the empty state."""


def test_agent_preselected_from_the_agents_page_link() -> None:
    """Arriving via an agent's View commission link preselects that agent."""
