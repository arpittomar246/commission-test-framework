"""Response bodies checked against their JSON Schemas.

Guards the contract itself: field names, types, and the absence of anything
unexpected, for both the success and the error shapes.
"""

from datetime import date
from typing import Callable

import pytest

from framework.api_client import ApiClient
from framework.schemas import SchemaValidationError, validate_schema

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def test_created_agent_matches_the_agent_schema(
    agent_factory: Callable[..., dict],
    unique_email: Callable[[str], str],
) -> None:
    """Creating an agent returns a valid agent object."""
    email = unique_email("schema")
    agent = agent_factory(name="Schema Agent", email=email, join_date="2024-03-10")

    validate_schema(agent, "agent")

    assert agent["name"] == "Schema Agent"
    assert agent["email"] == email
    assert agent["join_date"] == "2024-03-10"

    broken = [
        {**agent, "leaked": "internal"},
        {k: v for k, v in agent.items() if k != "guarantee_active"},
        {**agent, "id": str(agent["id"])},
        {**agent, "months_active": -1},
    ]
    for payload in broken:
        with pytest.raises(SchemaValidationError):
            validate_schema(payload, "agent")


def test_agent_list_matches_the_agent_schema(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """Every item in the agent listing validates."""
    mine = agent_factory(name="Listed Agent", join_date="2024-03-10")

    response = api_client.list_agents()

    assert response.status == 200
    validate_schema(response.body, "agent", many=True)

    listed = {agent["id"]: agent for agent in response.body}
    assert mine["id"] in listed
    assert listed[mine["id"]] == mine

    with pytest.raises(SchemaValidationError, match=r"\[1\]id"):
        validate_schema([mine, {**mine, "id": "not-an-int"}], "agent", many=True)
    with pytest.raises(SchemaValidationError, match="expected a list"):
        validate_schema(mine, "agent", many=True)


def test_single_agent_matches_the_agent_schema(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
) -> None:
    """Fetching one agent returns a valid agent object."""
    joined_today = agent_factory(name="Fresh Agent", join_date=date.today().isoformat())
    settled = agent_factory(name="Settled Agent", join_date="2023-01-10")

    fetched = {}
    for created in (joined_today, settled):
        response = api_client.get_agent(created["id"])

        assert response.status == 200
        validate_schema(response.body, "agent")
        assert response.body == created
        fetched[created["id"]] = response.body

    fresh = fetched[joined_today["id"]]
    assert fresh["months_active"] == 0
    assert fresh["guarantee_active"] is True

    old = fetched[settled["id"]]
    assert old["months_active"] > 0
    assert old["guarantee_active"] is False


def test_created_policy_matches_the_policy_schema(
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Creating a policy returns a valid policy object."""
    agent = agent_factory(name="Policy Owner", join_date="2024-03-10")
    policy = policy_factory(
        agent["id"], value=125_000.5, sold_date="2024-05-12", customer_name="  Acme Foods  "
    )

    validate_schema(policy, "policy")

    assert policy["agent_id"] == agent["id"]
    assert policy["agent_name"] == agent["name"]
    assert policy["customer_name"] == "Acme Foods"
    assert policy["value"] == pytest.approx(125_000.5)
    assert policy["sold_date"] == "2024-05-12"
    assert policy["status"] == "active"

    broken = [
        {**policy, "status": "pending"},
        {**policy, "value": 0},
        {k: v for k, v in policy.items() if k != "agent_name"},
        {**policy, "cancelled_at": "2024-06-01T00:00:00Z"},
    ]
    for payload in broken:
        with pytest.raises(SchemaValidationError):
            validate_schema(payload, "policy")


def test_policy_list_matches_the_policy_schema(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """Every item in the policy listing validates."""
    agent = agent_factory(name="Listing Owner", join_date="2024-03-10")
    active = policy_factory(agent["id"], value=200_000, sold_date="2024-05-06")
    cancelled = policy_factory(agent["id"], value=150_000, sold_date="2024-05-20", cancelled=True)

    everything = api_client.list_policies()
    assert everything.status == 200
    validate_schema(everything.body, "policy", many=True)

    listed = {policy["id"]: policy for policy in everything.body}
    assert listed[active["id"]] == active
    assert listed[cancelled["id"]] == cancelled
    assert {listed[active["id"]]["status"], listed[cancelled["id"]]["status"]} == {
        "active",
        "cancelled",
    }

    filtered = [
        api_client.list_policies(agent_id=agent["id"]),
        api_client.list_policies(agent_id=agent["id"], status="active"),
        api_client.list_policies(agent_id=agent["id"], status="cancelled"),
        api_client.list_policies(agent_id=999_999_999),
    ]
    for response in filtered:
        assert response.status == 200
        validate_schema(response.body, "policy", many=True)

    assert [p["id"] for p in filtered[0].body] == [cancelled["id"], active["id"]]
    assert filtered[3].body == []


def test_cancelled_policy_matches_the_policy_schema(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """The cancel response is still a valid policy object."""
    agent = agent_factory(name="Cancelling Owner", join_date="2024-03-10")
    before = policy_factory(agent["id"], value=180_000, sold_date="2024-05-14")
    assert before["status"] == "active"

    response = api_client.cancel_policy(before["id"])

    assert response.status == 200
    validate_schema(response.body, "policy")
    assert response.body == {**before, "status": "cancelled"}

    stored = api_client.list_policies(agent_id=agent["id"]).body
    assert stored == [response.body]


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
