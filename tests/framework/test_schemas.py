"""The framework's schema validator.

Runs without the app: every payload here is built by hand, so the only thing
under test is how ``validate_schema`` reads the schema files. Marked ``api`` so
the API job in CI picks it up.
"""

import pytest

from framework.schemas import SchemaValidationError, validate_schema

pytestmark = pytest.mark.api

VALID = {
    "agent": {
        "id": 1, "name": "Priya", "email": "priya@example.com", "join_date": "2024-03-10",
        "months_active": 2, "guarantee_active": True,
    },
    "policy": {
        "id": 1, "agent_id": 1, "agent_name": "Priya", "customer_name": "Acme",
        "value": 100_000.0, "sold_date": "2024-05-12", "status": "active",
    },
    "commission": {
        "agent_id": 1, "month": "2024-05", "gross_commission": 0.0, "clawback": 0.0,
        "subtotal": 0.0, "guarantee_applied": False, "final_payout": 0.0, "policy_count": 0,
    },
    "error": {"detail": "No agent with id 1", "code": "AGENT_NOT_FOUND"},
}

PATTERNED_FIELDS = [
    ("agent", "email"),
    ("agent", "join_date"),
    ("policy", "sold_date"),
    ("commission", "month"),
    ("error", "code"),
]


@pytest.mark.parametrize(("schema", "field"), PATTERNED_FIELDS)
def test_a_trailing_newline_does_not_satisfy_a_pattern(schema: str, field: str) -> None:
    """A pattern ending in $ means the end of the string, not the end of a line."""
    clean = VALID[schema]
    validate_schema(clean, schema)

    padded = {**clean, field: clean[field] + "\n"}
    with pytest.raises(SchemaValidationError, match=field):
        validate_schema(padded, schema)
