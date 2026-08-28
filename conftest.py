"""Shared pytest fixtures for the API, UI and parity suites.

Data fixtures create their rows through the public API -- the same door a user
goes through -- and clean up afterwards by deleting straight from SQLite,
since the API deliberately exposes no destructive endpoints.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterator
from datetime import date

import pytest

from framework.api_client import ApiClient
from framework.config import config
from pages.agents_page import AgentsPage
from pages.commission_page import CommissionPage
from pages.policies_page import PoliciesPage


# --------------------------------------------------------------------------- #
# database helpers
# --------------------------------------------------------------------------- #


def _connect() -> sqlite3.Connection:
    """Open the app's SQLite file directly, for setup and teardown only."""
    return sqlite3.connect(str(config.db_path))


def _delete_agents(agent_ids: list[int]) -> None:
    """Remove agents and everything they sold."""
    if not agent_ids:
        return
    placeholders = ",".join("?" * len(agent_ids))
    with _connect() as conn:
        conn.execute(f"DELETE FROM policies WHERE agent_id IN ({placeholders})", agent_ids)
        conn.execute(f"DELETE FROM agents WHERE id IN ({placeholders})", agent_ids)


def _delete_policies(policy_ids: list[int]) -> None:
    """Remove individual policies."""
    if not policy_ids:
        return
    placeholders = ",".join("?" * len(policy_ids))
    with _connect() as conn:
        conn.execute(f"DELETE FROM policies WHERE id IN ({placeholders})", policy_ids)


# --------------------------------------------------------------------------- #
# api
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def api_client() -> Iterator[ApiClient]:
    """One HTTP session shared by the whole run."""
    client = ApiClient(config)
    yield client
    client.close()


@pytest.fixture(scope="session")
def app_config():
    """The resolved framework configuration."""
    return config


@pytest.fixture
def reset_db() -> Iterator[None]:
    """Empty both tables before the test, and again after it.

    Destructive by design -- mark tests that use it ``serial`` (or keep them out
    of an ``-n`` run) so parallel workers do not pull data out from under
    each other.
    """
    def wipe() -> None:
        with _connect() as conn:
            conn.execute("DELETE FROM policies")
            conn.execute("DELETE FROM agents")

    wipe()
    yield
    wipe()


# --------------------------------------------------------------------------- #
# data factories
# --------------------------------------------------------------------------- #


@pytest.fixture
def unique_email() -> Callable[[str], str]:
    """Build an email that will not collide with another test's agent."""
    counter = {"n": 0}

    def make(prefix: str = "agent") -> str:
        counter["n"] += 1
        return f"{prefix}.{os.getpid()}.{id(counter)}.{counter['n']}@example.com"

    return make


@pytest.fixture
def agent_factory(
    api_client: ApiClient, unique_email: Callable[[str], str]
) -> Iterator[Callable[..., dict]]:
    """Create agents on demand; every one is removed at the end of the test."""
    created: list[int] = []

    def make(
        name: str = "Test Agent",
        join_date: str | None = None,
        email: str | None = None,
    ) -> dict:
        response = api_client.create_agent(
            name=name,
            email=email or unique_email("agent"),
            join_date=join_date or date.today().isoformat(),
        )
        if response.status != 201:
            raise RuntimeError(f"agent_factory could not create an agent: {response.body}")
        created.append(response.body["id"])
        return response.body

    yield make
    _delete_agents(created)


@pytest.fixture
def new_agent(agent_factory: Callable[..., dict]) -> dict:
    """A single freshly created agent who joined today, cleaned up afterwards."""
    return agent_factory(name="Test Agent")


@pytest.fixture
def policy_factory(api_client: ApiClient) -> Iterator[Callable[..., dict]]:
    """Create policies on demand; every one is removed at the end of the test."""
    created: list[int] = []

    def make(
        agent_id: int,
        value: float = 100_000.0,
        sold_date: str | None = None,
        customer_name: str = "Test Customer",
        cancelled: bool = False,
    ) -> dict:
        response = api_client.create_policy(
            agent_id=agent_id,
            customer_name=customer_name,
            value=value,
            sold_date=sold_date or date.today().isoformat(),
        )
        if response.status != 201:
            raise RuntimeError(f"policy_factory could not create a policy: {response.body}")
        policy = response.body
        created.append(policy["id"])
        if cancelled:
            policy = api_client.cancel_policy(policy["id"]).body
        return policy

    yield make
    _delete_policies(created)


# --------------------------------------------------------------------------- #
# playwright
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    """Honour HEADLESS and SLOW_MO from the environment."""
    return {**browser_type_launch_args, "headless": config.headless, "slow_mo": config.slow_mo}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Point every context at BASE_URL with a predictable viewport."""
    return {
        **browser_context_args,
        "base_url": config.base_url,
        "viewport": {"width": 1440, "height": 900},
    }


@pytest.fixture
def agents_page(page) -> AgentsPage:
    """The /agents page object, already open."""
    return AgentsPage(page).goto()


@pytest.fixture
def policies_page(page) -> PoliciesPage:
    """The /policies page object, already open."""
    return PoliciesPage(page).goto()


@pytest.fixture
def commission_page(page) -> CommissionPage:
    """The /commission page object, already open."""
    return CommissionPage(page).goto()
