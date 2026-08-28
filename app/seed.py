"""Populate the database with a small, deterministic demo dataset.

Five agents with join dates spread either side of the three-month guarantee
window, and twenty policies mixing active and cancelled so that clawbacks,
guarantee top-ups and plain months are all represented.

Run it with::

    python -m app.seed
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.database import SessionLocal, init_db
from app.models import STATUS_ACTIVE, STATUS_CANCELLED, Agent, Policy

# (name, email, months before today the agent joined)
AGENTS: list[tuple[str, str, int]] = [
    ("Priya Sharma", "priya.sharma@example.com", 0),
    ("Rahul Menon", "rahul.menon@example.com", 1),
    ("Ananya Iyer", "ananya.iyer@example.com", 2),
    ("Vikram Desai", "vikram.desai@example.com", 5),
    ("Neha Kulkarni", "neha.kulkarni@example.com", 14),
]

# (agent index, customer, value, months before today it was sold, cancelled)
POLICIES: list[tuple[int, str, float, int, bool]] = [
    (0, "Sunrise Logistics", 90_000, 0, False),
    (0, "Kestrel Foods", 150_000, 0, True),
    (0, "Bluewave Marine", 60_000, 1, False),
    (1, "Northgate Textiles", 450_000, 0, False),
    (1, "Harbour Point Cafe", 120_000, 0, True),
    (1, "Silverline Motors", 300_000, 1, False),
    (1, "Copperfield Estates", 80_000, 2, True),
    (2, "Lakeview Dental", 200_000, 0, False),
    (2, "Ridgeway Haulage", 175_000, 1, True),
    (2, "Amber Retail Group", 640_000, 1, False),
    (2, "Foxglove Nurseries", 95_000, 3, False),
    (3, "Ironbridge Steel", 820_000, 0, False),
    (3, "Marlow Consulting", 240_000, 0, False),
    (3, "Pinecrest Schools", 310_000, 1, True),
    (3, "Halcyon Media", 155_000, 2, False),
    (3, "Verdant Farms", 275_000, 4, False),
    (4, "Ozone Aviation", 1_100_000, 0, False),
    (4, "Meridian Shipping", 520_000, 1, True),
    (4, "Cobalt Analytics", 365_000, 2, False),
    (4, "Willowbrook Homes", 210_000, 5, False),
]


def shift_months(day: date, months: int) -> date:
    """Move ``day`` back by ``months`` calendar months, clamping the day-of-month."""
    total = day.year * 12 + (day.month - 1) - months
    year, month = total // 12, total % 12 + 1
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(day.day, last_day))


def seed(today: date | None = None) -> None:
    """Wipe the agent and policy tables, then insert the demo dataset."""
    today = today or date.today()
    init_db()

    with SessionLocal() as db:
        db.query(Policy).delete()
        db.query(Agent).delete()
        db.commit()

        agents: list[Agent] = []
        for name, email, months_ago in AGENTS:
            agent = Agent(name=name, email=email, join_date=shift_months(today, months_ago))
            db.add(agent)
            agents.append(agent)
        db.commit()

        for index, customer, value, months_ago, cancelled in POLICIES:
            sold = shift_months(today, months_ago)
            db.add(
                Policy(
                    agent_id=agents[index].id,
                    customer_name=customer,
                    value=value,
                    sold_date=sold,
                    status=STATUS_CANCELLED if cancelled else STATUS_ACTIVE,
                    cancelled_at=(
                        datetime.now(timezone.utc) if cancelled else None
                    ),
                )
            )
        db.commit()

    print(f"Seeded {len(AGENTS)} agents and {len(POLICIES)} policies (today = {today}).")


if __name__ == "__main__":
    seed()
