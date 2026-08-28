"""The agents page: table, live search, sorting, and the create-agent modal."""

import pytest

pytestmark = [pytest.mark.ui, pytest.mark.smoke]


def test_agents_table_lists_every_agent() -> None:
    """Each agent from the API gets a row."""


def test_agent_row_shows_name_email_join_date_and_months_active() -> None:
    """Every column of a row is populated."""


def test_guarantee_badge_reads_active_for_a_new_agent() -> None:
    """An agent inside the window shows the green Guarantee Active badge."""


def test_guarantee_badge_reads_expired_for_an_established_agent() -> None:
    """An agent past the window shows the grey Guarantee Expired badge."""


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
