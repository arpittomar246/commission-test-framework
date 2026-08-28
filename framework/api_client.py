"""A thin, explicit HTTP client for the commission API.

One method per endpoint, so tests read as calls against the product rather
than against ``requests``.  Every method returns an :class:`ApiResponse`
carrying the status, the decoded body and how long the call took -- nothing
raises on a 4xx, because most of the interesting tests are about error
responses.

Only 5xx responses are retried, and only because a flaky server is never the
thing under test.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

from framework.config import Config, config as default_config

RETRY_STATUSES = frozenset({500, 502, 503, 504})


@dataclass
class ApiResponse:
    """One HTTP exchange, unpacked into the parts assertions care about."""

    status: int
    body: Any
    elapsed_ms: float
    headers: dict[str, str] = field(default_factory=dict)
    attempts: int = 1

    @property
    def ok(self) -> bool:
        """Whether the status is in the 2xx range."""
        return 200 <= self.status < 300

    @property
    def code(self) -> str | None:
        """The API's machine-readable error code, when the body carries one."""
        return self.body.get("code") if isinstance(self.body, dict) else None

    @property
    def detail(self) -> str | None:
        """The API's human-readable error message, when the body carries one."""
        return self.body.get("detail") if isinstance(self.body, dict) else None


class ApiClient:
    """Session-backed wrapper around the JSON API."""

    def __init__(
        self,
        cfg: Config | None = None,
        *,
        max_retries: int = 2,
        retry_backoff: float = 0.25,
    ) -> None:
        self.config = cfg or default_config
        self.base_url = self.config.api_url
        self.timeout = self.config.timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )
        self.history: list[ApiResponse] = []

    # ------------------------------------------------------------- plumbing --

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> ApiResponse:
        """Send one request, retrying only on 5xx, and record the timing."""
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            response = self.session.request(
                method, url, json=json, params=params, timeout=self.timeout
            )
            elapsed_ms = (time.perf_counter() - started) * 1000

            if response.status_code in RETRY_STATUSES and attempt <= self.max_retries:
                time.sleep(self.retry_backoff * attempt)
                continue

            try:
                body = response.json() if response.content else None
            except ValueError:
                body = response.text

            result = ApiResponse(
                status=response.status_code,
                body=body,
                elapsed_ms=round(elapsed_ms, 2),
                headers=dict(response.headers),
                attempts=attempt,
            )
            self.history.append(result)
            return result

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()

    # --------------------------------------------------------------- agents --

    def create_agent(self, name: str, email: str, join_date: str) -> ApiResponse:
        """POST /api/agents"""
        return self.request(
            "POST", "/agents", json={"name": name, "email": email, "join_date": join_date}
        )

    def create_agent_raw(self, payload: dict[str, Any]) -> ApiResponse:
        """POST /api/agents with an arbitrary payload, for validation tests."""
        return self.request("POST", "/agents", json=payload)

    def list_agents(self) -> ApiResponse:
        """GET /api/agents"""
        return self.request("GET", "/agents")

    def get_agent(self, agent_id: int) -> ApiResponse:
        """GET /api/agents/{id}"""
        return self.request("GET", f"/agents/{agent_id}")

    # -------------------------------------------------------------- policies --

    def create_policy(
        self, agent_id: int, customer_name: str, value: float, sold_date: str
    ) -> ApiResponse:
        """POST /api/policies"""
        return self.request(
            "POST",
            "/policies",
            json={
                "agent_id": agent_id,
                "customer_name": customer_name,
                "value": value,
                "sold_date": sold_date,
            },
        )

    def create_policy_raw(self, payload: dict[str, Any]) -> ApiResponse:
        """POST /api/policies with an arbitrary payload, for validation tests."""
        return self.request("POST", "/policies", json=payload)

    def list_policies(
        self, agent_id: int | None = None, status: str | None = None
    ) -> ApiResponse:
        """GET /api/policies with optional ``agent_id`` and ``status`` filters."""
        params: dict[str, Any] = {}
        if agent_id is not None:
            params["agent_id"] = agent_id
        if status is not None:
            params["status"] = status
        return self.request("GET", "/policies", params=params or None)

    def cancel_policy(self, policy_id: int) -> ApiResponse:
        """POST /api/policies/{id}/cancel"""
        return self.request("POST", f"/policies/{policy_id}/cancel")

    # ------------------------------------------------------------ commission --

    def get_commission(self, agent_id: int, month: str) -> ApiResponse:
        """GET /api/agents/{id}/commission?month=YYYY-MM"""
        return self.request("GET", f"/agents/{agent_id}/commission", params={"month": month})

    def get_commission_history(self, agent_id: int, month: str) -> ApiResponse:
        """GET /api/agents/{id}/commission/history?month=YYYY-MM"""
        return self.request(
            "GET", f"/agents/{agent_id}/commission/history", params={"month": month}
        )

    def get_stats(self) -> ApiResponse:
        """GET /api/stats"""
        return self.request("GET", "/stats")
