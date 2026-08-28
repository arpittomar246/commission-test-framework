"""The policies page: table, filters, the create modal and the cancel flow."""

import pytest

pytestmark = [pytest.mark.ui, pytest.mark.smoke]


def test_policies_table_lists_every_policy() -> None:
    """Each policy from the API gets a row."""


def test_policy_row_shows_id_customer_agent_value_and_sold_date() -> None:
    """Every column of a row is populated."""


def test_active_policy_shows_a_green_active_badge() -> None:
    """An uncancelled policy is badged Active."""


def test_cancelled_policy_shows_a_red_cancelled_badge() -> None:
    """A cancelled policy is badged Cancelled."""


def test_agent_filter_narrows_the_table_to_one_agent() -> None:
    """Picking an agent hides every other agent's policies."""


def test_status_filter_narrows_the_table_to_one_status() -> None:
    """Picking a status hides policies in the other state."""


def test_both_filters_apply_together() -> None:
    """Agent and status filters compose."""


def test_filters_with_no_matches_show_the_no_results_state() -> None:
    """A combination matching nothing shows the empty-filter message."""


def test_cancel_button_opens_the_confirmation_modal() -> None:
    """The confirmation modal appears and names the policy."""


def test_confirming_a_cancellation_updates_the_badge_and_toasts() -> None:
    """Confirming flips the row to Cancelled and shows a success toast."""


def test_dismissing_the_confirmation_leaves_the_policy_active() -> None:
    """Backing out changes nothing."""


def test_cancelled_policies_offer_no_cancel_button() -> None:
    """An already-cancelled row has no cancel action."""


def test_cancel_failure_shows_an_error_toast() -> None:
    """A rejected cancellation surfaces the error toast."""


def test_add_policy_modal_lists_every_agent_in_its_dropdown() -> None:
    """The agent dropdown is populated from the API."""


def test_creating_a_policy_adds_a_row_and_shows_a_success_toast() -> None:
    """A valid submission closes the modal, refreshes the table and toasts."""


def test_empty_state_shows_when_there_are_no_policies() -> None:
    """With an empty database the page offers the empty state."""
