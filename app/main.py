"""FastAPI application: JSON API plus the server-rendered portal shell.

Every failure -- validation, missing row, conflicting state -- leaves through
:func:`error`, so each one has the same body shape::

    {"detail": "...", "code": "..."}
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import commission as rules
from app.database import get_db, init_db
from app.models import STATUS_ACTIVE, STATUS_CANCELLED, Agent, Policy
from app.schemas import AgentCreate, AgentOut, CommissionOut, PolicyCreate, PolicyOut

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Make sure the schema exists before the first request lands."""
    init_db()
    yield


app = FastAPI(title="Commission Portal", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# --------------------------------------------------------------------------- #
# errors
# --------------------------------------------------------------------------- #


def error(status: int, code: str, detail: str) -> JSONResponse:
    """Build the single error response shape used across the API."""
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})


class ApiError(Exception):
    """An expected failure that should surface as a coded JSON error."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    """Render an :class:`ApiError` as JSON."""
    return error(exc.status, exc.code, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Answer malformed or incomplete payloads with a 400 rather than a 422."""
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part != "body")
    return error(400, "VALIDATION_ERROR", f"{field or 'payload'}: {first['msg']}")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _today() -> date:
    """Today's date, isolated so there is one place to reason about "now"."""
    return date.today()


def _agent_out(agent: Agent, today: date | None = None) -> AgentOut:
    """Project an agent row into its API representation."""
    today = today or _today()
    return AgentOut(
        id=agent.id,
        name=agent.name,
        email=agent.email,
        join_date=agent.join_date,
        months_active=max(rules.months_active(agent.join_date, today), 0),
        guarantee_active=rules.is_guarantee_active(agent.join_date, rules.month_key(today)),
    )


def _policy_out(policy: Policy) -> PolicyOut:
    """Project a policy row into its API representation."""
    return PolicyOut(
        id=policy.id,
        agent_id=policy.agent_id,
        agent_name=policy.agent.name,
        customer_name=policy.customer_name,
        value=policy.value,
        sold_date=policy.sold_date,
        status=policy.status,
    )


def _get_agent(db: Session, agent_id: int) -> Agent:
    """Fetch an agent or raise a 404 AGENT_NOT_FOUND."""
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise ApiError(404, "AGENT_NOT_FOUND", f"No agent with id {agent_id}")
    return agent


def _records(agent: Agent) -> list[rules.PolicyRecord]:
    """Convert an agent's policies into the rule engine's input type."""
    return [
        rules.PolicyRecord(
            id=p.id,
            value=p.value,
            sold_date=p.sold_date,
            cancelled=p.is_cancelled,
        )
        for p in agent.policies
    ]


# --------------------------------------------------------------------------- #
# agents
# --------------------------------------------------------------------------- #


@app.post("/api/agents", response_model=AgentOut, status_code=201)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> AgentOut:
    """Create an agent."""
    name = payload.name.strip()
    email = payload.email.strip()
    if not name:
        raise ApiError(400, "INVALID_NAME", "name must not be empty")
    if not EMAIL_PATTERN.match(email):
        raise ApiError(400, "INVALID_EMAIL", f"{payload.email} is not a valid email")
    if db.scalar(select(Agent).where(Agent.email == email)) is not None:
        raise ApiError(409, "DUPLICATE_EMAIL", f"{email} is already registered")

    agent = Agent(name=name, email=email, join_date=payload.join_date)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@app.get("/api/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)) -> list[AgentOut]:
    """List every agent, newest first."""
    today = _today()
    agents = db.scalars(select(Agent).order_by(Agent.id.desc())).unique().all()
    return [_agent_out(a, today) for a in agents]


@app.get("/api/agents/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db)) -> AgentOut:
    """Fetch one agent by id."""
    return _agent_out(_get_agent(db, agent_id))


# --------------------------------------------------------------------------- #
# policies
# --------------------------------------------------------------------------- #


@app.post("/api/policies", response_model=PolicyOut, status_code=201)
def create_policy(payload: PolicyCreate, db: Session = Depends(get_db)) -> PolicyOut:
    """Create a policy for an existing agent."""
    if payload.value <= 0:
        raise ApiError(400, "INVALID_VALUE", "value must be greater than zero")
    if not payload.customer_name.strip():
        raise ApiError(400, "INVALID_CUSTOMER", "customer_name must not be empty")
    _get_agent(db, payload.agent_id)

    policy = Policy(
        agent_id=payload.agent_id,
        customer_name=payload.customer_name.strip(),
        value=payload.value,
        sold_date=payload.sold_date,
        status=STATUS_ACTIVE,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _policy_out(policy)


@app.get("/api/policies", response_model=list[PolicyOut])
def list_policies(
    agent_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[PolicyOut]:
    """List policies, optionally narrowed by agent and/or status."""
    if status is not None and status not in (STATUS_ACTIVE, STATUS_CANCELLED):
        raise ApiError(400, "INVALID_STATUS", f"unknown status {status}")

    query = select(Policy).order_by(Policy.id.desc())
    if agent_id is not None:
        query = query.where(Policy.agent_id == agent_id)
    if status is not None:
        query = query.where(Policy.status == status)
    return [_policy_out(p) for p in db.scalars(query).unique().all()]


@app.post("/api/policies/{policy_id}/cancel", response_model=PolicyOut)
def cancel_policy(policy_id: int, db: Session = Depends(get_db)) -> PolicyOut:
    """Cancel a policy; cancelling one twice is a conflict."""
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise ApiError(404, "POLICY_NOT_FOUND", f"No policy with id {policy_id}")
    if policy.is_cancelled:
        raise ApiError(409, "ALREADY_CANCELLED", f"Policy {policy_id} is already cancelled")

    policy.status = STATUS_CANCELLED
    policy.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return _policy_out(policy)


# --------------------------------------------------------------------------- #
# commission
# --------------------------------------------------------------------------- #


@app.get("/api/agents/{agent_id}/commission", response_model=CommissionOut)
def get_commission(agent_id: int, month: str, db: Session = Depends(get_db)) -> CommissionOut:
    """Calculate one agent's payout for one YYYY-MM month."""
    agent = _get_agent(db, agent_id)
    try:
        breakdown = rules.calculate_commission(agent.join_date, month, _records(agent))
    except rules.InvalidMonthError as exc:
        raise ApiError(400, "INVALID_MONTH", str(exc)) from exc

    return CommissionOut(agent_id=agent.id, **vars(breakdown))


@app.get("/api/agents/{agent_id}/commission/history")
def commission_history(agent_id: int, month: str, db: Session = Depends(get_db)) -> dict:
    """Final payouts for the six months ending at ``month`` -- feeds the chart."""
    agent = _get_agent(db, agent_id)
    try:
        months = rules.recent_months(month, 6)
    except rules.InvalidMonthError as exc:
        raise ApiError(400, "INVALID_MONTH", str(exc)) from exc

    records = _records(agent)
    return {
        "agent_id": agent.id,
        "months": months,
        "payouts": [
            rules.calculate_commission(agent.join_date, m, records).final_payout
            for m in months
        ],
    }


@app.get("/api/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict:
    """Headline numbers for the dashboard cards."""
    today = _today()
    this_month = rules.month_key(today)
    agents = db.scalars(select(Agent)).unique().all()
    policies = db.scalars(select(Policy)).unique().all()

    payout = sum(
        rules.calculate_commission(a.join_date, this_month, _records(a)).final_payout
        for a in agents
    )
    cancelled_this_month = sum(
        1
        for p in policies
        if p.cancelled_at is not None and rules.month_key(p.cancelled_at.date()) == this_month
    )
    return {
        "month": this_month,
        "total_agents": len(agents),
        "active_policies": sum(1 for p in policies if not p.is_cancelled),
        "cancelled_this_month": cancelled_this_month,
        "total_payout": round(payout, 2),
    }


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #


def _page(request: Request, template: str, title: str, active: str) -> HTMLResponse:
    """Render one of the four portal pages."""
    return templates.TemplateResponse(
        request, template, {"page_title": title, "active_nav": active}
    )


@app.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request) -> HTMLResponse:
    """Dashboard page."""
    return _page(request, "dashboard.html", "Dashboard", "dashboard")


@app.get("/agents", response_class=HTMLResponse)
def page_agents(request: Request) -> HTMLResponse:
    """Agents page."""
    return _page(request, "agents.html", "Agents", "agents")


@app.get("/policies", response_class=HTMLResponse)
def page_policies(request: Request) -> HTMLResponse:
    """Policies page."""
    return _page(request, "policies.html", "Policies", "policies")


@app.get("/commission", response_class=HTMLResponse)
def page_commission(request: Request) -> HTMLResponse:
    """Commission page."""
    return _page(request, "commission.html", "Commission", "commission")
