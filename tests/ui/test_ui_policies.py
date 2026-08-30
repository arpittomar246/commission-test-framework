"""The policies page: table, filters, the create modal and the cancel flow.

The ``policies_page`` fixture opens the page before a test body runs, so any
test that creates its rows first has to ``reload()`` before asserting -- the
table is rendered once at load from ``GET /api/policies``.

Rows are created against an ``agent_factory`` agent wherever possible: tearing
that agent down takes its policies with it, including the ones this suite
creates through the UI rather than through the API.
"""

from typing import Callable

import pytest
from playwright.sync_api import expect

from framework.api_client import ApiClient
from pages.policies_page import PoliciesPage

pytestmark = [pytest.mark.ui, pytest.mark.smoke]

SOLD_DATE = "2024-05-08"


def _as_number(displayed: str) -> float:
    """Strip the en-IN grouping the table renders money with."""
    return float(displayed.replace(",", ""))


def test_policies_table_lists_every_policy(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Each policy from the API gets a row."""
    # Scoped to an agent this test owns. Comparing the table against every
    # policy in the database races other workers under ``-n auto``, which are
    # free to create and delete rows between the page load and the API call.
    agent = agent_factory(name="Table Listing Agent")
    for day in (4, 11, 18):
        policy_factory(agent["id"], sold_date=f"{SOLD_DATE[:8]}{day:02d}")
    policies_page.reload()
    policies_page.filter_by_agent(agent["id"])

    expected = {p["id"] for p in api_client.list_policies(agent_id=agent["id"]).body}

    assert len(expected) == 3
    assert set(policies_page.row_ids()) == expected
    assert policies_page.row_count() == len(expected)


def test_policy_row_shows_id_customer_agent_value_and_sold_date(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Every column of a row is populated."""
    agent = agent_factory(name="Row Rendering Agent")
    policy = policy_factory(
        agent["id"], value=250_000, sold_date=SOLD_DATE, customer_name="Acme Foods"
    )
    policies_page.reload()

    pid = policy["id"]
    assert policies_page.customer_of(pid) == "Acme Foods"
    assert policies_page.agent_of(pid) == "Row Rendering Agent"
    assert policies_page.value_of(pid) == "2,50,000.00"
    assert _as_number(policies_page.value_of(pid)) == 250_000.00
    assert policies_page.sold_date_of(pid) == SOLD_DATE
    assert policies_page.get_text("policy-cell-id-{}".format(pid)) == "#{}".format(pid)


def test_active_policy_shows_a_green_active_badge(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """An uncancelled policy is badged Active."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE)
    policies_page.reload()

    assert policies_page.status_of(policy["id"]) == "active"
    assert policies_page.status_label(policy["id"]) == "Active"


def test_cancelled_policy_shows_a_red_cancelled_badge(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """A cancelled policy is badged Cancelled."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE, cancelled=True)
    policies_page.reload()

    assert policies_page.status_of(policy["id"]) == "cancelled"
    assert policies_page.status_label(policy["id"]) == "Cancelled"


def test_agent_filter_narrows_the_table_to_one_agent(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Picking an agent hides every other agent's policies."""
    mine = agent_factory(name="Filter Mine")
    theirs = agent_factory(name="Filter Theirs")
    kept = [policy_factory(mine["id"], sold_date=SOLD_DATE)["id"] for _ in range(2)]
    hidden = policy_factory(theirs["id"], sold_date=SOLD_DATE)["id"]
    policies_page.reload()

    policies_page.filter_by_agent(mine["id"])

    assert set(policies_page.row_ids()) == set(kept)
    assert hidden not in policies_page.row_ids()


def test_status_filter_narrows_the_table_to_one_status(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Picking a status hides policies in the other state."""
    agent = agent_factory()
    policy_factory(agent["id"], sold_date=SOLD_DATE)
    policy_factory(agent["id"], sold_date=SOLD_DATE, cancelled=True)
    policies_page.reload()

    policies_page.filter_by_status("cancelled")

    statuses = policies_page.statuses()
    assert statuses, "the cancelled filter hid every row"
    assert set(statuses) == {"cancelled"}


def test_both_filters_apply_together(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Agent and status filters compose."""
    agent = agent_factory(name="Composed Filters")
    active = policy_factory(agent["id"], sold_date=SOLD_DATE)["id"]
    policy_factory(agent["id"], sold_date=SOLD_DATE, cancelled=True)
    policies_page.reload()

    policies_page.filter_by_agent(agent["id"])
    policies_page.filter_by_status("active")

    assert policies_page.row_ids() == [active]


def test_filters_with_no_matches_show_the_no_results_state(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """A combination matching nothing shows the empty-filter message."""
    agent = agent_factory(name="Only Active")
    policy_factory(agent["id"], sold_date=SOLD_DATE)
    policies_page.reload()

    policies_page.filter_by_agent(agent["id"])
    policies_page.filter_by_status("cancelled")

    assert policies_page.row_count() == 0
    assert policies_page.is_visible(PoliciesPage.NO_RESULTS)
    assert not policies_page.is_visible(PoliciesPage.EMPTY_STATE)


def test_cancel_button_opens_the_confirmation_modal(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """The confirmation modal appears and names the policy."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE, customer_name="Blue Harbour")
    policies_page.reload()

    policies_page.open_cancel_modal(policy["id"])

    assert policies_page.modal_is_open(PoliciesPage.CANCEL_MODAL)
    assert policies_page.cancel_modal_label() == "#{} - Blue Harbour".format(policy["id"])


def test_confirming_a_cancellation_updates_the_badge_and_toasts(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Confirming flips the row to Cancelled and shows a success toast."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE)
    policies_page.reload()

    policies_page.cancel_policy(policy["id"])

    expected = "Policy #{} cancelled".format(policy["id"])
    assert policies_page.wait_for_toast("success") == expected
    expect(policies_page.status_badge(policy["id"])).to_have_attribute(
        "data-status", "cancelled"
    )
    policies_page.wait_for_modal_closed(PoliciesPage.CANCEL_MODAL)


def test_dismissing_the_confirmation_leaves_the_policy_active(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """Backing out changes nothing."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE)
    policies_page.reload()

    policies_page.open_cancel_modal(policy["id"])
    policies_page.dismiss_cancel()

    policies_page.wait_for_modal_closed(PoliciesPage.CANCEL_MODAL)
    assert policies_page.status_of(policy["id"]) == "active"
    assert policies_page.toast_count("success") == 0


def test_cancelled_policies_offer_no_cancel_button(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """An already-cancelled row has no cancel action."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE, cancelled=True)
    policies_page.reload()

    expect(policies_page.cancel_button(policy["id"])).to_have_count(0)
    assert policies_page.is_visible("policy-cancelled-note-{}".format(policy["id"]))


def test_cancel_failure_shows_an_error_toast(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """A rejected cancellation surfaces the error toast."""
    agent = agent_factory()
    policy = policy_factory(agent["id"], sold_date=SOLD_DATE)
    policies_page.reload()

    # Cancel behind the page's back, so its button is stale and the retry 409s.
    assert api_client.cancel_policy(policy["id"]).status == 200

    policies_page.cancel_policy(policy["id"])

    assert "already cancelled" in policies_page.wait_for_toast("error").lower()
    assert policies_page.toast_count("success") == 0


def test_add_policy_modal_lists_every_agent_in_its_dropdown(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """The agent dropdown is populated from the API."""
    agent_factory(name="Dropdown Agent")
    policies_page.reload()

    policies_page.open_add_modal()

    options = policies_page.agent_select_options()
    assert options[0] == "Select an agent"
    assert "Dropdown Agent" in options
    # No count against the live agent list: other workers add and remove agents
    # between this page load and any later call. Uniqueness is the invariant
    # that actually matters -- fillAgentOptions() must not double-append.
    assert len(options) == len(set(options))


def test_creating_a_policy_adds_a_row_and_shows_a_success_toast(
    agent_factory: Callable[..., dict],
    policies_page: PoliciesPage,
) -> None:
    """A valid submission closes the modal, refreshes the table and toasts."""
    agent = agent_factory(name="Creator Agent")
    policies_page.reload()
    # Filter to this test's own agent first, so the row count it watches cannot
    # be moved by policies other workers create. The filter survives the
    # re-render that follows a successful create.
    policies_page.filter_by_agent(agent["id"])
    expect(policies_page.rows()).to_have_count(0)

    policies_page.create_policy(agent["id"], "Northwind Ltd", "125000", SOLD_DATE)

    message = policies_page.wait_for_toast("success")
    assert message.startswith("Policy #")
    policies_page.wait_for_modal_closed(PoliciesPage.MODAL)
    expect(policies_page.rows()).to_have_count(1)

    new_id = int(message.removeprefix("Policy #").split()[0])
    assert policies_page.customer_of(new_id) == "Northwind Ltd"
    assert policies_page.agent_of(new_id) == "Creator Agent"
    assert _as_number(policies_page.value_of(new_id)) == 125_000.00


@pytest.mark.serial
def test_empty_state_shows_when_there_are_no_policies(
    reset_db: None,
    policies_page: PoliciesPage,
) -> None:
    """With an empty database the page offers the empty state."""
    policies_page.reload()

    assert policies_page.row_count() == 0
    assert policies_page.is_visible(PoliciesPage.EMPTY_STATE)
    assert not policies_page.is_visible(PoliciesPage.NO_RESULTS)
    assert policies_page.is_visible("policies-empty-cta")
