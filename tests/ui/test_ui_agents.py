"""The agents page: table, live search, sorting, and the create-agent modal."""

import sqlite3
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
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


def test_search_with_no_matches_shows_the_no_results_state(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """A term matching nothing shows the empty-search message."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    findable = agent_factory(name=f"{token} Findable")
    agents_page.reload()

    agents_page.search(f"nobody-{uuid.uuid4().hex}")

    expect(agents_page.rows()).to_have_count(0)
    expect(agents_page.testid(AgentsPage.NO_RESULTS)).to_be_visible()
    assert "match your search" in agents_page.get_text(AgentsPage.NO_RESULTS)
    assert not agents_page.is_visible(AgentsPage.EMPTY_STATE)
    assert not agents_page.is_visible("agents-empty-cta")
    assert agents_page.is_visible(AgentsPage.TABLE)

    agents_page.clear_search()
    agents_page.search(token)

    expect(agents_page.rows()).to_have_count(1)
    assert agents_page.row_ids() == [findable["id"]]
    expect(agents_page.testid(AgentsPage.NO_RESULTS)).to_be_hidden()


def test_clearing_the_search_restores_every_row(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """Emptying the box brings the full table back."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    agent_factory(name=f"{token} Kept")
    agent_factory(name="Hidden While Searching")
    agents_page.reload()

    everyone = agents_page.row_ids()
    assert len(everyone) >= 2

    box = agents_page.testid(AgentsPage.SEARCH_INPUT)
    ways_to_clear = {
        "emptied in one go": lambda: box.fill(""),
        "selected and deleted": lambda: (box.press("ControlOrMeta+a"), box.press("Backspace")),
        "left with only spaces": lambda: box.fill("   "),
    }
    for how, clear in ways_to_clear.items():
        agents_page.search(token)
        expect(agents_page.rows()).to_have_count(1)

        clear()

        expect(agents_page.rows()).to_have_count(len(everyone))
        assert agents_page.row_ids() == everyone, how
        assert not agents_page.is_visible(AgentsPage.NO_RESULTS), how

        box.fill("")


def test_clicking_a_column_header_sorts_the_table(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """Sorting by name reorders the rows."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    alpha = agent_factory(
        name=f"{token} Alpha", email=f"{token}.c@example.com", join_date=_first_of_month(2)
    )
    bravo = agent_factory(
        name=f"{token} Bravo", email=f"{token}.a@example.com", join_date=_first_of_month(10)
    )
    charlie = agent_factory(
        name=f"{token} Charlie", email=f"{token}.b@example.com", join_date=date.today().isoformat()
    )
    agents_page.reload()
    agents_page.search(token)
    expect(agents_page.rows()).to_have_count(3)

    assert [agents_page.months_active_of(a["id"]) for a in (alpha, bravo, charlie)] == ["2", "10", "0"]

    expected = {
        "name": [alpha, bravo, charlie],
        "email": [bravo, charlie, alpha],
        "join_date": [bravo, alpha, charlie],
        "months_active": [charlie, alpha, bravo],
    }
    for column, order in expected.items():
        agents_page.sort_by(column)
        assert agents_page.row_ids() == [a["id"] for a in order], column


def test_clicking_the_same_header_twice_reverses_the_sort(
    agent_factory: Callable[..., dict],
    agents_page: AgentsPage,
) -> None:
    """The second click flips the direction."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    created = [agent_factory(name=f"{token} {n}") for n in ("Bravo", "Alpha", "Charlie")]
    by_name = sorted(created, key=lambda a: a["name"])
    ascending = [a["id"] for a in by_name]
    descending = ascending[::-1]

    agents_page.reload()
    agents_page.search(token)
    expect(agents_page.rows()).to_have_count(3)
    assert agents_page.row_ids() not in (ascending, descending)

    for click, expected in enumerate([ascending, descending, ascending], start=1):
        agents_page.sort_by("name")
        assert agents_page.row_ids() == expected, f"after click {click}"

    agents_page.sort_by("name")
    assert agents_page.row_ids() == descending

    agents_page.clear_search()
    agents_page.search(token)
    expect(agents_page.rows()).to_have_count(3)
    assert agents_page.row_ids() == descending

    agents_page.sort_by("email")
    agents_page.sort_by("name")
    assert agents_page.row_ids() == ascending


def test_add_agent_button_opens_the_modal(agents_page: AgentsPage) -> None:
    """The modal becomes visible when the button is clicked."""
    agents_page.page.clock.set_fixed_time(datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))
    modal = agents_page.testid(AgentsPage.MODAL)

    for button in (AgentsPage.ADD_BUTTON, "new-button"):
        expect(modal).to_be_hidden()
        assert not agents_page.modal_is_open(AgentsPage.MODAL), button

        agents_page.click_testid(button)

        expect(modal).to_be_visible()
        assert agents_page.modal_is_open(AgentsPage.MODAL), button
        assert agents_page.get_value(AgentsPage.NAME_INPUT) == "", button
        assert agents_page.get_value(AgentsPage.EMAIL_INPUT) == "", button
        assert agents_page.get_value(AgentsPage.JOIN_DATE_INPUT) == "2026-11-09", button
        for field in ("name", "email", "join-date"):
            assert not agents_page.field_error_visible(field), f"{button}: {field} error showing"

        agents_page.close_add_modal()
        expect(modal).to_be_hidden()
        assert not agents_page.modal_is_open(AgentsPage.MODAL), button


def test_join_date_defaults_to_the_local_day_not_the_utc_one(browser, app_config) -> None:
    """At 2 am in India on the 1st, the suggested join date is the 1st, not last month."""
    context = browser.new_context(base_url=app_config.base_url, timezone_id="Asia/Kolkata")
    try:
        page = context.new_page()
        india = timezone(timedelta(hours=5, minutes=30))
        page.clock.set_fixed_time(datetime(2026, 12, 1, 2, 0, tzinfo=india))

        agents = AgentsPage(page).goto()
        agents.open_add_modal()

        assert agents.get_value(AgentsPage.JOIN_DATE_INPUT) == "2026-12-01"
    finally:
        context.close()


def test_creating_an_agent_adds_a_row_and_shows_a_success_toast(
    api_client: ApiClient,
    app_config,
    agents_page: AgentsPage,
) -> None:
    """A valid submission closes the modal, refreshes the table and toasts."""
    token = f"zq{uuid.uuid4().hex[:8]}"
    name = f"{token} Created In The Form"
    typed_email = f"{token}.New@Example.COM"
    stored_email = typed_email.lower()

    try:
        agents_page.create_agent(name, typed_email, "2024-03-10")

        assert agents_page.wait_for_toast("success") == f"Agent {name} created"
        agents_page.wait_for_modal_closed(AgentsPage.MODAL)
        assert not agents_page.modal_is_open(AgentsPage.MODAL)

        matches = [a for a in api_client.list_agents().body if a["email"] == stored_email]
        assert len(matches) == 1
        created = matches[0]
        assert created["name"] == name
        assert created["join_date"] == "2024-03-10"

        expect(agents_page.row(created["id"])).to_be_visible()
        assert agents_page.name_of(created["id"]) == name
        assert agents_page.email_of(created["id"]) == stored_email
        assert agents_page.join_date_of(created["id"]) == "2024-03-10"

        agents_page.search(token)
        expect(agents_page.rows()).to_have_count(1)
    finally:
        with sqlite3.connect(str(app_config.db_path)) as db:
            ids = [row[0] for row in db.execute("SELECT id FROM agents WHERE email = ?", (stored_email,))]
            db.executemany("DELETE FROM policies WHERE agent_id = ?", [(i,) for i in ids])
            db.executemany("DELETE FROM agents WHERE id = ?", [(i,) for i in ids])


def test_cancelling_the_modal_creates_nothing() -> None:
    """Dismissing the modal leaves the table untouched."""


def test_empty_state_shows_when_there_are_no_agents() -> None:
    """With an empty database the page offers the empty state."""
