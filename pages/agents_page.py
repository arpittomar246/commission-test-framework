"""Page object for /agents -- locators and actions only, no assertions."""

from __future__ import annotations

from playwright.sync_api import Locator

from pages.base_page import BasePage


class AgentsPage(BasePage):
    """The agents table, its search/sort controls and the create-agent modal."""

    path = "/agents"

    TABLE = "agents-table"
    TABLE_BODY = "agents-table-body"
    SEARCH_INPUT = "agent-search-input"
    ADD_BUTTON = "add-agent-button"
    EMPTY_STATE = "agents-empty-state"
    NO_RESULTS = "agents-no-results"

    MODAL = "agent-modal"
    MODAL_CLOSE = "agent-modal-close"
    NAME_INPUT = "agent-name-input"
    EMAIL_INPUT = "agent-email-input"
    JOIN_DATE_INPUT = "agent-join-date-input"
    SUBMIT_BUTTON = "agent-submit-button"
    CANCEL_BUTTON = "agent-cancel-button"
    FORM_ERROR = "agent-form-error"

    SORT_HEADERS = {
        "name": "agents-sort-name",
        "email": "agents-sort-email",
        "join_date": "agents-sort-join-date",
        "months_active": "agents-sort-months-active",
    }

    # ----------------------------------------------------------------- table --

    def row(self, agent_id: int) -> Locator:
        """Locator for one agent's row."""
        return self.testid(f"agent-row-{agent_id}")

    def rows(self) -> Locator:
        """Locator matching every rendered agent row."""
        return self.testid(self.TABLE_BODY).locator('[data-testid^="agent-row-"]')

    def row_count(self) -> int:
        """How many agent rows are currently rendered."""
        return self.rows().count()

    def name_of(self, agent_id: int) -> str:
        """Name cell for one agent."""
        return self.get_text(f"agent-cell-name-{agent_id}")

    def email_of(self, agent_id: int) -> str:
        """Email cell for one agent."""
        return self.get_text(f"agent-cell-email-{agent_id}")

    def join_date_of(self, agent_id: int) -> str:
        """Join-date cell for one agent."""
        return self.get_text(f"agent-cell-join-date-{agent_id}")

    def months_active_of(self, agent_id: int) -> str:
        """Months-active cell for one agent."""
        return self.get_text(f"agent-cell-months-active-{agent_id}")

    def guarantee_badge(self, agent_id: int) -> Locator:
        """Locator for one agent's guarantee badge."""
        return self.testid(f"guarantee-badge-{agent_id}")

    def guarantee_state(self, agent_id: int) -> str | None:
        """``"active"`` or ``"expired"``, read from the badge's data attribute."""
        return self.guarantee_badge(agent_id).get_attribute("data-guarantee")

    def guarantee_label(self, agent_id: int) -> str:
        """Text shown on one agent's guarantee badge."""
        return self.get_text(f"guarantee-badge-{agent_id}")

    def visible_names(self) -> list[str]:
        """Every name currently rendered, in display order."""
        cells = self.testid(self.TABLE_BODY).locator('[data-testid^="agent-cell-name-"]')
        return [(cells.nth(i).inner_text() or "").strip() for i in range(cells.count())]

    def row_ids(self) -> list[int]:
        """Ids of the rendered rows, in display order."""
        rows = self.rows()
        ids: list[int] = []
        for i in range(rows.count()):
            testid = rows.nth(i).get_attribute("data-testid") or ""
            ids.append(int(testid.rsplit("-", 1)[-1]))
        return ids

    # -------------------------------------------------------------- controls --

    def search(self, term: str) -> None:
        """Type into the live search box."""
        self.type_testid(self.SEARCH_INPUT, term)

    def clear_search(self) -> None:
        """Empty the search box."""
        self.fill_testid(self.SEARCH_INPUT, "")

    def sort_by(self, column: str) -> None:
        """Click a sortable column header: name, email, join_date, months_active."""
        self.click_testid(self.SORT_HEADERS[column])

    def open_commission_for(self, agent_id: int) -> None:
        """Follow an agent's 'View commission' link."""
        self.click_testid(f"agent-commission-link-{agent_id}")
        self.page.wait_for_load_state("networkidle")

    # ----------------------------------------------------------------- modal --

    def open_add_modal(self) -> None:
        """Open the create-agent modal and wait for it."""
        self.click_testid(self.ADD_BUTTON)
        self.wait_for_modal(self.MODAL)

    def close_add_modal(self) -> None:
        """Dismiss the modal via its Cancel button."""
        self.click_testid(self.CANCEL_BUTTON)

    def fill_agent_form(self, name: str, email: str, join_date: str) -> None:
        """Fill the three fields of the create-agent form."""
        self.fill_testid(self.NAME_INPUT, name)
        self.fill_testid(self.EMAIL_INPUT, email)
        self.fill_testid(self.JOIN_DATE_INPUT, join_date)

    def submit_agent_form(self) -> None:
        """Submit the create-agent form."""
        self.click_testid(self.SUBMIT_BUTTON)

    def create_agent(self, name: str, email: str, join_date: str) -> None:
        """Open the modal, fill it in and submit -- the whole happy path."""
        self.open_add_modal()
        self.fill_agent_form(name, email, join_date)
        self.submit_agent_form()

    def field_error(self, field: str) -> str:
        """Text of an inline field error: name, email or join-date."""
        return self.get_text(f"agent-{field}-error")

    def field_error_visible(self, field: str) -> bool:
        """Whether an inline field error is showing."""
        return self.testid(f"agent-{field}-error").is_visible()

    def form_error(self) -> str:
        """Text of the modal's form-level error banner."""
        return self.get_text(self.FORM_ERROR)
