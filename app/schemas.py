"""Pydantic request and response models.

Field-level constraints are deliberately loose: the app answers every bad
payload with a 400 and a ``{"detail", "code"}`` body, so the interesting checks
live in the route handlers where a specific error code can be attached.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class AgentCreate(BaseModel):
    """Payload for creating an agent."""

    name: str
    email: str
    join_date: date


class AgentOut(BaseModel):
    """An agent as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    join_date: date
    months_active: int
    guarantee_active: bool


class PolicyCreate(BaseModel):
    """Payload for creating a policy."""

    agent_id: int
    customer_name: str
    value: float
    sold_date: date


class PolicyOut(BaseModel):
    """A policy as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    agent_name: str
    customer_name: str
    value: float
    sold_date: date
    status: str


class CommissionOut(BaseModel):
    """A month's commission breakdown for one agent."""

    agent_id: int
    month: str
    gross_commission: float
    clawback: float
    subtotal: float
    guarantee_applied: bool
    final_payout: float
    policy_count: int


class ErrorOut(BaseModel):
    """The one error shape every failing endpoint returns."""

    detail: str
    code: str
