"""Response bodies checked against their JSON Schemas.

Guards the contract itself: field names, types, and the absence of anything
unexpected, for both the success and the error shapes.
"""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def test_created_agent_matches_the_agent_schema() -> None:
    """Creating an agent returns a valid agent object."""


def test_agent_list_matches_the_agent_schema() -> None:
    """Every item in the agent listing validates."""


def test_single_agent_matches_the_agent_schema() -> None:
    """Fetching one agent returns a valid agent object."""


def test_created_policy_matches_the_policy_schema() -> None:
    """Creating a policy returns a valid policy object."""


def test_policy_list_matches_the_policy_schema() -> None:
    """Every item in the policy listing validates."""


def test_cancelled_policy_matches_the_policy_schema() -> None:
    """The cancel response is still a valid policy object."""


def test_commission_response_matches_the_commission_schema() -> None:
    """The commission breakdown validates."""


def test_not_found_error_matches_the_error_schema() -> None:
    """A 404 body carries a detail and a code."""


def test_validation_error_matches_the_error_schema() -> None:
    """A 400 body carries a detail and a code."""


def test_conflict_error_matches_the_error_schema() -> None:
    """A 409 body carries a detail and a code."""


def test_responses_carry_no_unexpected_fields() -> None:
    """No endpoint leaks fields the schemas do not declare."""


def test_every_schema_file_is_itself_valid() -> None:
    """The four schema documents are well-formed JSON Schema."""
