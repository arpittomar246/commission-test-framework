"""SQLAlchemy models for agents and policies."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

STATUS_ACTIVE = "active"
STATUS_CANCELLED = "cancelled"


class Base(DeclarativeBase):
    """Declarative base for every model in the app."""


class Agent(Base):
    """An insurance agent who sells policies and earns commission."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    join_date: Mapped[date] = mapped_column(Date, nullable=False)

    policies: Mapped[list["Policy"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Policy(Base):
    """A policy sold by an agent, either still active or cancelled."""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    sold_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_ACTIVE)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    agent: Mapped[Agent] = relationship(back_populates="policies", lazy="joined")

    @property
    def is_cancelled(self) -> bool:
        """Whether this policy has been cancelled."""
        return self.status == STATUS_CANCELLED
