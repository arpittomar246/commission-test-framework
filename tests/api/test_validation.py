"""Input validation and error handling across the API.

Every failure comes back with the same body shape -- a detail and a code --
and the status the endpoint contract promises.
"""

import sqlite3
from typing import Callable

import pytest

from framework.api_client import ApiClient

pytestmark = [pytest.mark.api, pytest.mark.smoke]

SOLD_DATE = "2024-05-12"
ERROR_KEYS = {"detail", "code"}

# Far beyond any id SQLite will hand out in a test run. Picking "highest id
# plus one" instead would race other workers creating rows under -n auto.
MISSING_ID = 999_999_999


def test_policy_value_of_zero_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A zero-value policy returns 400."""
    response = api_client.create_policy(
        agent_id=new_agent["id"],
        customer_name="Zero Value Ltd",
        value=0,
        sold_date=SOLD_DATE,
    )

    assert response.status == 400
    assert response.code == "INVALID_VALUE"
    assert "greater than zero" in (response.detail or "")
    # The one error shape, with nothing else smuggled alongside it.
    assert set(response.body) == ERROR_KEYS

    # A rejected request must not leave a row behind.
    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.status == 200
    assert listed.body == []


def test_negative_policy_value_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A negative policy value returns 400."""
    # Both ends of the negative range: a hair below zero, where a ``< 0``
    # rounding slip would show, and a value too large to be an accident.
    for value in (-0.01, -250_000):
        response = api_client.create_policy(
            agent_id=new_agent["id"],
            customer_name="Negative Value Ltd",
            value=value,
            sold_date=SOLD_DATE,
        )

        assert response.status == 400, f"{value} was not rejected"
        assert response.code == "INVALID_VALUE"
        assert set(response.body) == ERROR_KEYS

    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.status == 200
    assert listed.body == []


def test_creating_a_policy_for_an_unknown_agent_returns_404(
    api_client: ApiClient,
) -> None:
    """An agent_id with no matching agent returns 404."""
    # Everything else in the payload is valid, so the missing agent is the
    # only reason left for the request to fail.
    response = api_client.create_policy(
        agent_id=MISSING_ID,
        customer_name="Orphan Policy Ltd",
        value=100_000,
        sold_date=SOLD_DATE,
    )

    assert response.status == 404
    assert response.code == "AGENT_NOT_FOUND"
    assert str(MISSING_ID) in (response.detail or "")
    assert set(response.body) == ERROR_KEYS

    # No orphaned row pointing at an agent that does not exist.
    listed = api_client.list_policies(agent_id=MISSING_ID)
    assert listed.status == 200
    assert listed.body == []


def test_fetching_an_unknown_agent_returns_404(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """Requesting a missing agent id returns 404."""
    # Control first: the same route answers 200 for an agent that exists, so
    # the 404 below is about absence rather than a broken route.
    found = api_client.get_agent(new_agent["id"])
    assert found.status == 200
    assert found.body["id"] == new_agent["id"]

    response = api_client.get_agent(MISSING_ID)

    assert response.status == 404
    assert response.code == "AGENT_NOT_FOUND"
    assert str(MISSING_ID) in (response.detail or "")
    assert set(response.body) == ERROR_KEYS


def test_commission_for_an_unknown_agent_returns_404(
    api_client: ApiClient,
) -> None:
    """The commission endpoint 404s for a missing agent."""
    breakdown = api_client.get_commission(MISSING_ID, "2024-05")
    assert breakdown.status == 404
    assert breakdown.code == "AGENT_NOT_FOUND"
    assert set(breakdown.body) == ERROR_KEYS

    # Both problems at once: the agent is looked up before the month is
    # parsed, so the missing agent is what gets reported.
    both_wrong = api_client.get_commission(MISSING_ID, "2026-13")
    assert both_wrong.status == 404
    assert both_wrong.code == "AGENT_NOT_FOUND"

    # The six-month history behind the chart goes through the same lookup.
    history = api_client.get_commission_history(MISSING_ID, "2024-05")
    assert history.status == 404
    assert history.code == "AGENT_NOT_FOUND"
    assert set(history.body) == ERROR_KEYS


def test_malformed_month_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A month like 2026-13 returns 400."""
    # Control: a well-formed month for the same agent is answered normally.
    assert api_client.get_commission(new_agent["id"], "2026-05").status == 200

    # Near-misses against ^\d{4}-(0[1-9]|1[0-2])$, each failing a different part.
    malformed = [
        "2026-13",      # month past December
        "2026-00",      # month before January
        "2026-5",       # month not zero-padded
        "2026/05",      # wrong separator
        "26-05",        # two-digit year
        "2026-05-01",   # a full date, not a month
        "May 2026",     # a human spelling
        "2026-05\n",    # trailing newline: a bare `$` matches just before it
    ]
    for month in malformed:
        response = api_client.get_commission(new_agent["id"], month)

        assert response.status == 400, f"{month!r} was not rejected"
        assert response.code == "INVALID_MONTH", f"{month!r} gave {response.code}"
        assert "YYYY-MM" in (response.detail or "")
        assert set(response.body) == ERROR_KEYS


def test_missing_month_parameter_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """Omitting the month query parameter returns 400."""
    # get_commission() always sends ?month=, so drop to the raw request.
    for path in (
        f"/agents/{new_agent['id']}/commission",
        f"/agents/{new_agent['id']}/commission/history",
    ):
        response = api_client.request("GET", path)

        # FastAPI's default here is 422; the app rewrites it so the error
        # contract holds for framework-level failures too.
        assert response.status == 400, f"{path} gave {response.status}"
        assert response.code == "VALIDATION_ERROR"
        assert "month" in (response.detail or "")
        assert set(response.body) == ERROR_KEYS

    # The reverse of the unknown-agent test: request validation runs before the
    # handler, so a missing month beats a missing agent.
    both_wrong = api_client.request("GET", f"/agents/{MISSING_ID}/commission")
    assert both_wrong.status == 400
    assert both_wrong.code == "VALIDATION_ERROR"


def test_missing_required_agent_fields_are_rejected(
    api_client: ApiClient,
    unique_email: Callable[[str], str],
) -> None:
    """A partial agent payload returns 400."""
    email = unique_email("partial")
    complete = {"name": "Partial Agent", "email": email, "join_date": "2024-03-10"}

    # Drop one field at a time, so each request is wrong in exactly one way.
    for missing in complete:
        payload = {k: v for k, v in complete.items() if k != missing}
        response = api_client.create_agent_raw(payload)

        assert response.status == 400, f"without {missing}: {response.status}"
        assert response.code == "VALIDATION_ERROR"
        # The handler strips "body" from the location, so the field is named
        # plainly -- "name: Field required", not "body.name: ...".
        assert (response.detail or "").startswith(f"{missing}:"), response.detail
        assert set(response.body) == ERROR_KEYS

    empty = api_client.create_agent_raw({})
    assert empty.status == 400
    assert empty.code == "VALIDATION_ERROR"

    # None of the partial payloads created an agent. Matching on this test's
    # own email keeps the check safe while other workers add agents.
    emails = {a["email"] for a in api_client.list_agents().body}
    assert email not in emails


def test_missing_required_policy_fields_are_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A partial policy payload returns 400."""
    complete = {
        "agent_id": new_agent["id"],
        "customer_name": "Partial Policy Ltd",
        "value": 100_000,
        "sold_date": SOLD_DATE,
    }

    for missing in complete:
        payload = {k: v for k, v in complete.items() if k != missing}
        response = api_client.create_policy_raw(payload)

        assert response.status == 400, f"without {missing}: {response.status}"
        assert response.code == "VALIDATION_ERROR"
        assert (response.detail or "").startswith(f"{missing}:"), response.detail
        assert set(response.body) == ERROR_KEYS

    # Nothing was created for this agent by any of the partial payloads.
    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.status == 200
    assert listed.body == []

    # Control, last so it cannot disturb the check above: the complete payload
    # is accepted, so each 400 really was down to the one missing field.
    # (new_agent's teardown removes this policy along with the agent.)
    assert api_client.create_policy_raw(complete).status == 201


def test_invalid_email_is_rejected(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    unique_email: Callable[[str], str],
) -> None:
    """An unparseable email address returns 400."""
    # Every bad address carries this token, so the persistence check at the
    # end can look for it without racing other workers' agents.
    token = unique_email("bad").split("@")[0]
    malformed = [
        token,                       # no @ at all
        f"{token}@",                 # nothing after the @
        f"@{token}.com",             # nothing before the @
        f"{token}@example",          # domain without a dot
        f"{token}@@example.com",     # two @ signs
        f"{token} x@example.com",    # space in the local part
        f"{token}@exa mple.com",     # space in the domain
        f"{token}@example.com\nx",   # newline inside the address
    ]
    for email in malformed:
        response = api_client.create_agent_raw(
            {"name": "Bad Email", "email": email, "join_date": "2024-03-10"}
        )

        assert response.status == 400, f"{email!r} was not rejected"
        assert response.code == "INVALID_EMAIL", f"{email!r} gave {response.code}"
        assert set(response.body) == ERROR_KEYS

    stored = [a["email"] for a in api_client.list_agents().body]
    assert not [e for e in stored if token in e], "a rejected email was stored"

    # Control: surrounding whitespace is trimmed rather than rejected, and the
    # address is stored clean. This is why a trailing newline -- unlike in
    # a month -- never reaches the pattern.
    good = unique_email("good")
    agent = agent_factory(email=f"  {good}\n")
    assert agent["email"] == good


def test_duplicate_email_is_rejected(
    api_client: ApiClient,
    agent_factory: Callable[..., dict],
    unique_email: Callable[[str], str],
) -> None:
    """Reusing an existing agent's email returns 409."""
    email = unique_email("taken")
    original = agent_factory(name="First Holder", email=email, join_date="2024-03-10")

    # A different name and join date: the conflict is keyed on email alone.
    exact = api_client.create_agent(name="Second Holder", email=email, join_date="2025-01-01")
    assert exact.status == 409
    assert exact.code == "DUPLICATE_EMAIL"
    assert email in (exact.detail or "")
    assert set(exact.body) == ERROR_KEYS

    # Emails are trimmed before the lookup, so padding does not dodge it.
    padded = api_client.create_agent(name="Third Holder", email=f"  {email}\n", join_date="2025-01-01")
    assert padded.status == 409
    assert padded.code == "DUPLICATE_EMAIL"

    # Mail systems treat addresses case-insensitively in practice, so a change
    # of case is the same inbox and has to be the same agent.
    shouted = api_client.create_agent(name="Fourth Holder", email=email.upper(), join_date="2025-01-01")
    assert shouted.status == 409
    assert shouted.code == "DUPLICATE_EMAIL"

    # And new addresses are stored lowercased, so the rule holds whichever
    # casing arrives first.
    mixed = unique_email("Mixed.Case")
    assert agent_factory(email=mixed)["email"] == mixed.lower()

    # The first agent is untouched, and is still the only one with the address.
    holders = [a for a in api_client.list_agents().body if a["email"] == email]
    assert [a["id"] for a in holders] == [original["id"]]
    assert holders[0]["name"] == "First Holder"


def test_cancelling_an_already_cancelled_policy_returns_409(
    api_client: ApiClient,
    app_config,
    agent_factory: Callable[..., dict],
    policy_factory: Callable[..., dict],
) -> None:
    """The second cancellation of one policy conflicts."""
    agent = agent_factory(join_date="2023-01-10")
    policy = policy_factory(agent["id"], value=300_000, sold_date="2024-05-15")

    first = api_client.cancel_policy(policy["id"])
    assert first.status == 200
    assert first.body["status"] == "cancelled"

    def cancelled_at() -> str | None:
        # Not part of the API response, so read it where it lives.
        with sqlite3.connect(str(app_config.db_path)) as db:
            row = db.execute(
                "SELECT cancelled_at FROM policies WHERE id = ?", (policy["id"],)
            ).fetchone()
        return row[0]

    stamped = cancelled_at()
    assert stamped is not None

    second = api_client.cancel_policy(policy["id"])

    assert second.status == 409
    assert second.code == "ALREADY_CANCELLED"
    assert str(policy["id"]) in (second.detail or "")
    assert set(second.body) == ERROR_KEYS

    # The refused attempt changed nothing: the original timestamp stands, and
    # the commission is clawed back once, not twice.
    assert cancelled_at() == stamped
    breakdown = api_client.get_commission(agent["id"], "2024-05").body
    assert breakdown["clawback"] == pytest.approx(30_000.0)
    assert breakdown["subtotal"] == pytest.approx(0.0)


def test_cancelling_an_unknown_policy_returns_404(
    api_client: ApiClient,
) -> None:
    """Cancelling a policy id that does not exist returns 404."""
    response = api_client.cancel_policy(MISSING_ID)

    assert response.status == 404
    # Its own code, not AGENT_NOT_FOUND: a client can tell which id was wrong.
    assert response.code == "POLICY_NOT_FOUND"
    assert str(MISSING_ID) in (response.detail or "")
    assert set(response.body) == ERROR_KEYS

    # An id that is not even a number never reaches the lookup: FastAPI rejects
    # the path itself, and the handler keeps the "path." prefix it only strips
    # for bodies.
    garbled = api_client.request("POST", "/policies/not-a-number/cancel")
    assert garbled.status == 400
    assert garbled.code == "VALIDATION_ERROR"
    assert (garbled.detail or "").startswith("path.policy_id:"), garbled.detail


def test_unknown_status_filter_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """An unrecognised status filter value returns 400."""
    # Control: both real statuses are accepted.
    for status in ("active", "cancelled"):
        assert api_client.list_policies(agent_id=new_agent["id"], status=status).status == 200

    unknown = [
        "archived",   # a plausible status the app does not have
        "ACTIVE",     # the match is exact, so case matters
        " active",    # and so does whitespace
        "",           # ?status= with nothing after it
    ]
    for status in unknown:
        response = api_client.list_policies(status=status)

        assert response.status == 400, f"{status!r} gave {response.status}"
        assert response.code == "INVALID_STATUS"
        assert set(response.body) == ERROR_KEYS

    # The contrast worth knowing: an agent_id that matches nobody is not an
    # error, just an empty result. Only the status has a fixed set of values.
    nobody = api_client.list_policies(agent_id=MISSING_ID)
    assert nobody.status == 200
    assert nobody.body == []


def test_non_numeric_policy_value_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A value that is not a number returns 400."""
    base = {"agent_id": new_agent["id"], "customer_name": "Typed Ltd", "sold_date": SOLD_DATE}

    not_numbers = [
        "lots",       # a word
        "100,000",    # a number with grouping, as a person would write it
        "",           # an empty string
        None,         # JSON null
        [],           # a list
        {},           # an object
    ]
    for value in not_numbers:
        response = api_client.create_policy_raw({**base, "value": value})

        assert response.status == 400, f"{value!r} gave {response.status}"
        # Caught by type checking before the route runs, so this is the
        # framework-level code -- not INVALID_VALUE from the `value <= 0` check.
        assert response.code == "VALIDATION_ERROR", f"{value!r} gave {response.code}"
        assert (response.detail or "").startswith("value:"), response.detail

    # Floats the type check lets through but no policy can be worth. None of
    # them fail `value <= 0` -- infinity is not <= 0, and NaN fails every
    # comparison -- so the app has to check for them itself.
    for value in ("NaN", "Infinity", "-Infinity", "1e400"):
        response = api_client.create_policy_raw({**base, "value": value})

        assert response.status == 400, f"{value!r} gave {response.status}"
        assert response.code == "INVALID_VALUE", f"{value!r} gave {response.code}"
        assert set(response.body) == ERROR_KEYS

    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.body == []

    # Control: a number sent as a string is still a number. Pydantic converts
    # it, and the policy is stored with the numeric value.
    as_text = api_client.create_policy_raw({**base, "value": "100000"})
    assert as_text.status == 201
    assert as_text.body["value"] == pytest.approx(100_000.0)


def test_malformed_date_is_rejected(
    api_client: ApiClient,
    new_agent: dict,
) -> None:
    """A sold_date that is not a real date returns 400."""
    base = {"agent_id": new_agent["id"], "customer_name": "Dated Ltd", "value": 100_000}

    malformed = [
        # Shaped like a date, but no such day exists.
        "2023-02-29",           # 29 February in a year that is not a leap year
        "2024-02-30",           # 30 February in any year
        "2024-04-31",           # 31st of a 30-day month
        "2024-13-01",           # month 13
        "2024-00-10",           # month 0
        # Real days written the wrong way.
        "12/05/2024",           # ambiguous: 12 May or 5 December?
        "2024-5-12",            # not zero-padded
        "20240512",             # no separators
        "2024-05-12T10:30:00",  # a moment, not a day
        " 2024-05-12",          # leading space
        "2024-05-12\n",         # trailing newline -- the slip that caught the month
        # Not a date at all.
        "",
        None,
    ]
    for sold_date in malformed:
        response = api_client.create_policy_raw({**base, "sold_date": sold_date})

        assert response.status == 400, f"{sold_date!r} gave {response.status}"
        assert response.code == "VALIDATION_ERROR", f"{sold_date!r} gave {response.code}"
        assert (response.detail or "").startswith("sold_date:"), response.detail

    listed = api_client.list_policies(agent_id=new_agent["id"])
    assert listed.body == []

    # Control, and the other half of the first case: 29 February in a leap
    # year is a real day, and is stored as given.
    leap = api_client.create_policy_raw({**base, "sold_date": "2024-02-29"})
    assert leap.status == 201
    assert leap.body["sold_date"] == "2024-02-29"


def test_every_error_response_carries_a_code() -> None:
    """No failure path returns a body without a machine-readable code."""
