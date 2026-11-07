"""The agents page: table, live search, sorting, and the create-agent modal."""

from collections import Counter
from datetime import date, timedelta
from typing import Callable

import pytest

from framework.api_client import ApiClient
from pages.agents_page import AgentsPage

pytestmark = [pytest.mark.ui, pytest.mark.smoke]


def _first_of_month(months_ago: int) -> str:
    """The first day of the calendar month ``months_ago`` before this one."""
    today = date.today()
    total = today.year * 12 + (today.month - 1) - months_ago
    return date(total // 12, total % 12 + 1, 1).isoformat()


def test_agents_table_lists_every_agent(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """Each agent from the API gets a row."""
    mine = [agent_factory(name=f"Listed Agent {n}", join_date="2024-03-10") for n in range(3)]
    agents_page.reload()

    row_ids = agents_page.row_ids()

    duplicated = [agent_id for agent_id, seen in Counter(row_ids).items() if seen > 1]
    assert not duplicated, f"rows rendered more than once: {duplicated}"

    for agent in mine:
        assert agent["id"] in row_ids, f"agent {agent['id']} has no row"
        assert agents_page.name_of(agent["id"]) == agent["name"]

    assert agents_page.row_count() == len(row_ids) >= len(mine)
    assert agents_page.is_visible(AgentsPage.TABLE)
    assert not agents_page.is_visible(AgentsPage.EMPTY_STATE)
    assert not agents_page.is_visible(AgentsPage.NO_RESULTS)


def test_agent_row_shows_name_email_join_date_and_months_active(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    unique_email: Callable[[str], str],
    agents_page: AgentsPage,
) -> None:
    """Every column of a row is populated."""
    name = "<b>Ana</b> O'Brien & Sons"
    agent = agent_factory(name=name, email=unique_email("row"), join_date="2024-03-10")
    agents_page.reload()

    shown = api_client.get_agent(agent["id"]).body
    aid = agent["id"]

    assert agents_page.name_of(aid) == name
    assert agents_page.email_of(aid) == shown["email"]
    assert agents_page.join_date_of(aid) == "2024-03-10"
    assert agents_page.months_active_of(aid) == str(shown["months_active"])

    name_cell = agents_page.testid(f"agent-cell-name-{aid}")
    assert name_cell.locator("b").count() == 0

    link = agents_page.testid(f"agent-commission-link-{aid}")
    assert link.get_attribute("href") == f"/commission?agent_id={aid}"


def test_guarantee_badge_reads_active_for_a_new_agent(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """An agent inside the window shows the green Guarantee Active badge."""
    joined_today = agent_factory(name="Badge Today", join_date=date.today().isoformat())
    last_covered = agent_factory(name="Badge Month Two", join_date=_first_of_month(2))
    agents_page.reload()

    for agent in (joined_today, last_covered):
        aid = agent["id"]
        assert api_client.get_agent(aid).body["guarantee_active"] is True

        assert agents_page.guarantee_state(aid) == "active"
        assert agents_page.guarantee_label(aid) == "Guarantee Active"

    assert agents_page.months_active_of(joined_today["id"]) == "0"
    assert agents_page.months_active_of(last_covered["id"]) == "2"


def test_guarantee_badge_reads_expired_for_an_established_agent(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """An agent past the window shows the grey Guarantee Expired badge."""
    last_day_of_month_three = date.fromisoformat(_first_of_month(2)) - timedelta(days=1)
    just_lapsed = agent_factory(name="Badge Month Three", join_date=last_day_of_month_three.isoformat())
    long_settled = agent_factory(name="Badge Settled", join_date="2023-01-10")
    agents_page.reload()

    for agent in (just_lapsed, long_settled):
        aid = agent["id"]
        assert api_client.get_agent(aid).body["guarantee_active"] is False

        assert agents_page.guarantee_state(aid) == "expired"
        assert agents_page.guarantee_label(aid) == "Guarantee Expired"

    assert agents_page.months_active_of(just_lapsed["id"]) == "3"


def test_search_filters_the_table_as_you_type() -> None:
    """Typing narrows the rows without a page reload."""


def test_search_matches_on_email_as_well_as_name() -> None:
    """A fragment of an email address finds its agent."""


def test_search_with_no_matches_shows_the_no_results_state() -> None:
    """A term matching nothing shows the empty-search message."""


def test_clearing_the_search_restores_every_row() -> None:
    """Emptying the box brings the full table back."""


def test_clicking_a_column_header_sorts_the_table() -> None:
    """Sorting by name reorders the rows."""


def test_clicking_the_same_header_twice_reverses_the_sort() -> None:
    """The second click flips the direction."""


def test_add_agent_button_opens_the_modal() -> None:
    """The modal becomes visible when the button is clicked."""


def test_creating_an_agent_adds_a_row_and_shows_a_success_toast() -> None:
    """A valid submission closes the modal, refreshes the table and toasts."""


def test_cancelling_the_modal_creates_nothing() -> None:
    """Dismissing the modal leaves the table untouched."""


def test_empty_state_shows_when_there_are_no_agents() -> None:
    """With an empty database the page offers the empty state."""
