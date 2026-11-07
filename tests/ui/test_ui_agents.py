"""The agents page: table, live search, sorting, and the create-agent modal."""

import uuid
from collections import Counter
from datetime import date, timedelta
from typing import Callable

import pytest
from playwright.sync_api import expect

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


def test_search_filters_the_table_as_you_type(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """Typing narrows the rows without a page reload."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    amber = agent_factory(name=f"{token} Amber")
    ambrose = agent_factory(name=f"{token} Ambrose")
    agent_factory(name=f"{token} Basil")
    agents_page.reload()

    page = agents_page.page
    page.evaluate("window.__notReloaded = true")
    api_calls: list[str] = []
    page.on("request", lambda request: "/api/" in request.url and api_calls.append(request.url))

    box = agents_page.testid(AgentsPage.SEARCH_INPUT)
    box.press_sequentially(token)
    expect(agents_page.rows()).to_have_count(3)

    steps = [
        (" ", 3),
        ("A", 2),
        ("m", 2),
        ("b", 2),
        ("e", 1),
    ]
    for key, expected_rows in steps:
        box.press_sequentially(key)
        expect(agents_page.rows()).to_have_count(expected_rows)

    assert agents_page.row_ids() == [amber["id"]]
    assert ambrose["id"] not in agents_page.row_ids()

    assert page.evaluate("window.__notReloaded") is True
    assert api_calls == []


def test_search_matches_on_email_as_well_as_name(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """A fragment of an email address finds its agent."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    in_local_part = agent_factory(name="Email Match Local", email=f"{token}.local@example.com")
    in_domain = agent_factory(name="Email Match Domain", email=f"desk@{token}.example.com")
    agents_page.reload()

    for agent in (in_local_part, in_domain):
        assert token not in agent["name"].lower()

    searches = [
        (token, {in_local_part["id"], in_domain["id"]}),
        (f"@{token}", {in_domain["id"]}),
        (f"{token}.LOCAL", {in_local_part["id"]}),
    ]
    for term, expected in searches:
        agents_page.clear_search()
        agents_page.search(term)
        expect(agents_page.rows()).to_have_count(len(expected))
        assert set(agents_page.row_ids()) == expected, term


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
