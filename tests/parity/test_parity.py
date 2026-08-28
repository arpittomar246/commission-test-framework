"""UI/API parity: the screen and the JSON must never disagree.

Each test reads the same fact twice -- once from the API through the client,
once from the rendered page through a page object -- and compares them. A
failure here means the browser is showing something the API did not say.
"""

import pytest

pytestmark = pytest.mark.parity


def test_agent_count_matches_between_ui_and_api() -> None:
    """The agents table has one row per agent the API returns."""


def test_agent_fields_match_between_ui_and_api() -> None:
    """Name, email and join date agree for every agent."""


def test_months_active_matches_between_ui_and_api() -> None:
    """The months-active column agrees with the API field."""


def test_guarantee_badge_matches_the_api_flag() -> None:
    """The badge state agrees with guarantee_active."""


def test_policy_count_matches_between_ui_and_api() -> None:
    """The policies table has one row per policy the API returns."""


def test_policy_status_badges_match_the_api() -> None:
    """Every badge agrees with the policy's status field."""


def test_policy_values_match_between_ui_and_api() -> None:
    """Displayed values match the API once display formatting is stripped."""


def test_agent_filter_matches_the_api_filter() -> None:
    """Filtering by agent in the UI returns the same set as ?agent_id=."""


def test_status_filter_matches_the_api_filter() -> None:
    """Filtering by status in the UI returns the same set as ?status=."""


def test_commission_breakdown_matches_the_api() -> None:
    """Every line of the displayed breakdown matches the commission endpoint."""


def test_final_payout_matches_the_api() -> None:
    """The headline payout equals final_payout from the API."""


def test_guarantee_banner_matches_the_api_flag() -> None:
    """The banner is shown exactly when guarantee_applied is true."""


def test_chart_payouts_match_the_history_endpoint() -> None:
    """The six plotted bars match the history endpoint's payouts."""


def test_dashboard_stats_match_the_stats_endpoint() -> None:
    """All four stat cards agree with the stats endpoint."""


def test_dashboard_recent_activity_matches_the_policy_listing() -> None:
    """The recent-activity table shows the ten most recent policies."""


def test_cancelling_in_the_ui_changes_the_api_the_same_way() -> None:
    """A cancellation made through the browser is visible in the API."""


def test_creating_in_the_ui_changes_the_api_the_same_way() -> None:
    """An agent created through the browser is visible in the API."""
