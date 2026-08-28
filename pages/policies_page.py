"""Page object for /policies -- locators and actions only, no assertions."""

from __future__ import annotations

from playwright.sync_api import Locator

from pages.base_page import BasePage


class PoliciesPage(BasePage):
    """The policies table, its filters, the create modal and the cancel modal."""

    path = "/policies"

    TABLE = "policies-table"
    TABLE_BODY = "policies-table-body"
    FILTER_AGENT = "policy-filter-agent"
    FILTER_STATUS = "policy-filter-status"
    ADD_BUTTON = "add-policy-button"
    EMPTY_STATE = "policies-empty-state"
    NO_RESULTS = "policies-no-results"

    MODAL = "policy-modal"
    MODAL_CLOSE = "policy-modal-close"
    AGENT_SELECT = "policy-agent-select"
    CUSTOMER_INPUT = "policy-customer-input"
    VALUE_INPUT = "policy-value-input"
    SOLD_DATE_INPUT = "policy-sold-date-input"
    SUBMIT_BUTTON = "policy-submit-button"
    CANCEL_FORM_BUTTON = "policy-cancel-form-button"
    FORM_ERROR = "policy-form-error"

    CANCEL_MODAL = "cancel-modal"
    CONFIRM_CANCEL_BUTTON = "confirm-cancel-button"
    DISMISS_CANCEL_BUTTON = "dismiss-cancel-button"
    CANCEL_MODAL_LABEL = "cancel-modal-policy-label"

    # ----------------------------------------------------------------- table --

    def row(self, policy_id: int) -> Locator:
        """Locator for one policy's row."""
        return self.testid(f"policy-row-{policy_id}")

    def rows(self) -> Locator:
        """Locator matching every rendered policy row."""
        return self.testid(self.TABLE_BODY).locator('[data-testid^="policy-row-"]')

    def row_count(self) -> int:
        """How many policy rows are currently rendered."""
        return self.rows().count()

    def row_ids(self) -> list[int]:
        """Ids of the rendered rows, in display order."""
        rows = self.rows()
        ids: list[int] = []
        for i in range(rows.count()):
            testid = rows.nth(i).get_attribute("data-testid") or ""
            ids.append(int(testid.rsplit("-", 1)[-1]))
        return ids

    def customer_of(self, policy_id: int) -> str:
        """Customer cell for one policy."""
        return self.get_text(f"policy-cell-customer-{policy_id}")

    def agent_of(self, policy_id: int) -> str:
        """Agent cell for one policy."""
        return self.get_text(f"policy-cell-agent-{policy_id}")

    def value_of(self, policy_id: int) -> str:
        """Value cell for one policy, as displayed."""
        return self.get_text(f"policy-cell-value-{policy_id}")

    def sold_date_of(self, policy_id: int) -> str:
        """Sold-date cell for one policy."""
        return self.get_text(f"policy-cell-sold-date-{policy_id}")

    def status_badge(self, policy_id: int) -> Locator:
        """Locator for one policy's status badge."""
        return self.testid(f"policy-status-{policy_id}")

    def status_of(self, policy_id: int) -> str | None:
        """``"active"`` or ``"cancelled"``, read from the badge's data attribute."""
        return self.status_badge(policy_id).get_attribute("data-status")

    def status_label(self, policy_id: int) -> str:
        """Text shown on one policy's status badge."""
        return self.get_text(f"policy-status-{policy_id}")

    def statuses(self) -> list[str | None]:
        """Status of every rendered row, in display order."""
        badges = self.testid(self.TABLE_BODY).locator('[data-testid^="policy-status-"]')
        return [badges.nth(i).get_attribute("data-status") for i in range(badges.count())]

    # --------------------------------------------------------------- filters --

    def filter_by_agent(self, agent_id: int | str) -> None:
        """Narrow the table to one agent; pass ``""`` for all agents."""
        self.select_testid(self.FILTER_AGENT, str(agent_id))

    def filter_by_status(self, status: str) -> None:
        """Narrow the table to a status; pass ``""`` for all statuses."""
        self.select_testid(self.FILTER_STATUS, status)

    def agent_filter_options(self) -> list[str]:
        """Labels of the agent filter's options."""
        return self.testid(self.FILTER_AGENT).locator("option").all_inner_texts()

    # ---------------------------------------------------------- create modal --

    def open_add_modal(self) -> None:
        """Open the create-policy modal and wait for it."""
        self.click_testid(self.ADD_BUTTON)
        self.wait_for_modal(self.MODAL)

    def close_add_modal(self) -> None:
        """Dismiss the create modal via its Cancel button."""
        self.click_testid(self.CANCEL_FORM_BUTTON)

    def fill_policy_form(
        self, agent_id: int | str, customer: str, value: str, sold_date: str
    ) -> None:
        """Fill every field of the create-policy form."""
        self.select_testid(self.AGENT_SELECT, str(agent_id))
        self.fill_testid(self.CUSTOMER_INPUT, customer)
        self.fill_testid(self.VALUE_INPUT, value)
        self.fill_testid(self.SOLD_DATE_INPUT, sold_date)

    def submit_policy_form(self) -> None:
        """Submit the create-policy form."""
        self.click_testid(self.SUBMIT_BUTTON)

    def create_policy(
        self, agent_id: int | str, customer: str, value: str, sold_date: str
    ) -> None:
        """Open the modal, fill it in and submit -- the whole happy path."""
        self.open_add_modal()
        self.fill_policy_form(agent_id, customer, value, sold_date)
        self.submit_policy_form()

    def agent_select_options(self) -> list[str]:
        """Labels of the create modal's agent dropdown."""
        return self.testid(self.AGENT_SELECT).locator("option").all_inner_texts()

    def field_error(self, field: str) -> str:
        """Text of an inline field error: agent, customer, value or sold-date."""
        return self.get_text(f"policy-{field}-error")

    def field_error_visible(self, field: str) -> bool:
        """Whether an inline field error is showing."""
        return self.testid(f"policy-{field}-error").is_visible()

    def form_error(self) -> str:
        """Text of the create modal's form-level error banner."""
        return self.get_text(self.FORM_ERROR)

    # ---------------------------------------------------------- cancel modal --

    def cancel_button(self, policy_id: int) -> Locator:
        """Locator for one row's 'Cancel policy' button."""
        return self.testid(f"policy-cancel-button-{policy_id}")

    def open_cancel_modal(self, policy_id: int) -> None:
        """Click a row's cancel button and wait for the confirmation modal."""
        self.click_testid(f"policy-cancel-button-{policy_id}")
        self.wait_for_modal(self.CANCEL_MODAL)

    def cancel_modal_label(self) -> str:
        """The policy the confirmation modal says it is about to cancel."""
        return self.get_text(self.CANCEL_MODAL_LABEL)

    def confirm_cancel(self) -> None:
        """Confirm the cancellation."""
        self.click_testid(self.CONFIRM_CANCEL_BUTTON)

    def dismiss_cancel(self) -> None:
        """Back out of the confirmation modal, keeping the policy."""
        self.click_testid(self.DISMISS_CANCEL_BUTTON)

    def cancel_policy(self, policy_id: int) -> None:
        """Open the confirmation modal and confirm -- the whole cancel flow."""
        self.open_cancel_modal(policy_id)
        self.confirm_cancel()
