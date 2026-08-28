"""JSON Schema definitions for the API's response bodies.

Schemas live as ``.json`` files next to this module so they stay readable and
could be handed to a non-Python consumer.  Load one by name and validate::

    validate_schema(response.body, "agent")
    validate_schema(response.body, "policy", many=True)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

SCHEMA_DIR = Path(__file__).resolve().parent

SCHEMA_NAMES = ("agent", "policy", "commission", "error")


class SchemaValidationError(AssertionError):
    """Raised when a payload does not match its schema.

    Subclasses ``AssertionError`` so a failure reads like a normal assertion
    in a pytest report rather than an unexpected crash.
    """


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    """Load the named schema, e.g. ``load_schema("agent")``."""
    path = SCHEMA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No schema named {name!r} in {SCHEMA_DIR}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(payload: Any, name: str, *, many: bool = False) -> Any:
    """Check ``payload`` against the named schema and hand it straight back.

    ``many=True`` validates a list of items against the item schema, so a
    collection endpoint can be checked with the same schema as a single one.
    Every violation in the payload is reported, not just the first.
    """
    validator = Draft202012Validator(load_schema(name))
    items = payload if many else [payload]

    if many and not isinstance(payload, list):
        raise SchemaValidationError(f"expected a list of {name!r} items, got {type(payload).__name__}")

    problems: list[str] = []
    for index, item in enumerate(items):
        for error in sorted(validator.iter_errors(item), key=lambda e: list(e.path)):
            where = ".".join(str(p) for p in error.path) or "<root>"
            prefix = f"[{index}]" if many else ""
            problems.append(f"{prefix}{where}: {error.message}")

    if problems:
        raise SchemaValidationError(
            f"payload does not match the {name!r} schema:\n  " + "\n  ".join(problems)
        )
    return payload


__all__ = [
    "SCHEMA_NAMES",
    "SchemaValidationError",
    "ValidationError",
    "load_schema",
    "validate_schema",
]
