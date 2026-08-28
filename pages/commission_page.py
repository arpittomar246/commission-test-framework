"""Page object for /commission -- locators and actions only, no assertions."""

from __future__ import annotations

import json

from playwright.sync_api import Locator

from pages.base_page import BasePage


class CommissionPage(BasePage):
    """The calculator controls, the payout breakdown, the chart and the table."""

    path = "/commission"

    AGENT_SELECT = "commission-agent-select"
    MONTH_INPUT = "commission-month-input"
    CALCULATE_BUTTON = "calculate-button"
    ERROR = "commission-error"

    RESULT_CARD = "commission-result-card"
    RESULT_AGENT = "commission-result-agent"
    RESULT_MONTH = "commission-result-month"
    GROSS = "gross-commission"
    CLAWBACK = "clawback"
    SUBTOTAL = "subtotal"
    GUARANTEE_APPLIED = "guarantee-applied"
    FINAL_PAYOUT = "final-payout"
    POLICY_COUNT = "policy-count"

    GUARANTEE_BANNER = "guarantee-banner"
    GUARANTEE_BANNER_AMOUNT = "guarantee-banner-amount"

    CHART = "commission-chart"
    POLICIES_CARD = "commission-policies-card"
    POLICIES_TABLE = "commission-policies-table"
    EMPTY_STATE = "commission-empty-state"

    # -------------------------------------------------------------- controls --

    def select_agent(self, agent_id: int | str) -> None:
        """Pick the agent to calculate for."""
        self.select_testid(self.AGENT_SELECT, str(agent_id))

    def set_month(self, month: str) -> None:
        """Set the month picker to a ``YYYY-MM`` value."""
        self.fill_testid(self.MONTH_INPUT, month)

    def click_calculate(self) -> None:
        """Run the calculation."""
        self.click_testid(self.CALCULATE_BUTTON)

    def calculate(self, agent_id: int | str, month: str) -> None:
        """Select an agent and month, then calculate -- the whole flow."""
        self.select_agent(agent_id)
        self.set_month(month)
        self.click_calculate()
        self.wait_for_testid(self.RESULT_CARD)

    def agent_options(self) -> list[str]:
        """Labels in the agent dropdown."""
        return self.testid(self.AGENT_SELECT).locator("option").all_inner_texts()

    def error_message(self) -> str:
        """Text of the controls' error banner."""
        return self.get_text(self.ERROR)

    def error_visible(self) -> bool:
        """Whether the controls' error banner is showing."""
        return self.testid(self.ERROR).is_visible()

    # ------------------------------------------------------------- breakdown --

    def result_visible(self) -> bool:
        """Whether the breakdown card is on screen."""
        return self.testid(self.RESULT_CARD).is_visible()

    def gross_commission(self) -> str:
        """Gross Commission line, as displayed."""
        return self.get_text(self.GROSS)

    def clawback(self) -> str:
        """Clawback line, as displayed."""
        return self.get_text(self.CLAWBACK)

    def subtotal(self) -> str:
        """Subtotal line, as displayed."""
        return self.get_text(self.SUBTOTAL)

    def guarantee_applied(self) -> str:
        """Guarantee Applied line -- ``"Yes"`` or ``"No"``."""
        return self.get_text(self.GUARANTEE_APPLIED)

    def final_payout(self) -> str:
        """Final Payout figure, as displayed."""
        return self.get_text(self.FINAL_PAYOUT)

    def policy_count(self) -> str:
        """Number of policies folded into the calculation."""
        return self.get_text(self.POLICY_COUNT)

    def result_month(self) -> str:
        """The month the displayed result is for."""
        return self.get_text(self.RESULT_MONTH)

    def result_agent(self) -> str:
        """The agent the displayed result is for."""
        return self.get_text(self.RESULT_AGENT)

    def as_number(self, testid: str) -> float:
        """Read a money field and strip the display formatting off it."""
        raw = self.get_text(testid)
        return float(raw.replace(",", "").replace("-", "", 1) or 0)

    # -------------------------------------------------------------- guarantee --

    def guarantee_banner(self) -> Locator:
        """Locator for the minimum-guarantee banner."""
        return self.testid(self.GUARANTEE_BANNER)

    def guarantee_banner_visible(self) -> bool:
        """Whether the guarantee banner is showing."""
        return self.guarantee_banner().is_visible()

    def guarantee_banner_text(self) -> str:
        """Full text of the guarantee banner."""
        return self.get_text(self.GUARANTEE_BANNER)

    def guarantee_banner_amount(self) -> str:
        """The amount the banner says the payout was raised to."""
        return self.get_text(self.GUARANTEE_BANNER_AMOUNT)

    # ------------------------------------------------------------------ chart --

    def chart(self) -> Locator:
        """Locator for the chart canvas."""
        return self.testid(self.CHART)

    def chart_months(self) -> list[str]:
        """The six month labels the chart was drawn with."""
        return json.loads(self.get_attribute(self.CHART, "data-months") or "[]")

    def chart_payouts(self) -> list[float]:
        """The six payout values the chart was drawn with."""
        return json.loads(self.get_attribute(self.CHART, "data-payouts") or "[]")

    # ----------------------------------------------------------------- table --

    def policy_rows(self) -> Locator:
        """Locator matching every row of the included-policies table."""
        return self.page.locator('[data-testid^="commission-policy-row-"]')

    def policy_row_count(self) -> int:
        """How many policies are listed as included."""
        return self.policy_rows().count()

    def policy_row(self, policy_id: int) -> Locator:
        """Locator for one included policy's row."""
        return self.testid(f"commission-policy-row-{policy_id}")

    def policy_commission(self, policy_id: int) -> str:
        """Per-policy commission cell, as displayed."""
        return self.get_text(f"commission-policy-commission-{policy_id}")

    def empty_state_visible(self) -> bool:
        """Whether the 'no policies this month' state is showing."""
        return self.testid(self.EMPTY_STATE).is_visible()
