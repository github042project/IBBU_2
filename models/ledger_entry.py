"""
Models for IB Wallet - Ledger Entry module.

Provides SQLAlchemy 2.0 models for double-entry ledger transactions.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .account import Base


class LedgerEntry(Base):
    """
    Represents a double-entry ledger transaction in IB Wallet.
    
    In double-entry bookkeeping, every transaction involves two accounts:
    a debit (source) account and a credit (destination) account.
    This model records the movement of funds from one account to another.
    
    The idempotency_key ensures that duplicate requests result in only one
    ledger entry being created, preventing accidental double-posting.
    
    Attributes:
        id: Unique ledger entry identifier (primary key)
        debit_account_id: Account ID from which funds are debited
        credit_account_id: Account ID to which funds are credited
        amount: Transaction amount stored as Decimal for precision
        currency: ISO 4217 currency code (e.g., INR, CHF)
        idempotency_key: Unique key for idempotent transaction processing
        created_at: Timestamp when the ledger entry was created (UTC)
    """

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Unique ledger entry identifier."""

    debit_account_id: Mapped[int] = mapped_column(nullable=False, index=True)
    """Account ID from which funds are debited (source account)."""

    credit_account_id: Mapped[int] = mapped_column(nullable=False, index=True)
    """Account ID to which funds are credited (destination account)."""

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=2), nullable=False
    )
    """Transaction amount stored as Decimal for financial precision."""

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    """ISO 4217 currency code (e.g., INR, CHF)."""

    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    """Unique idempotency key to prevent duplicate transactions."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    """Timestamp when the ledger entry was created (UTC)."""

    def __repr__(self) -> str:
        """
        Return string representation of the LedgerEntry.
        
        Returns:
            A detailed string representation including key transaction details.
        """
        return (
            f"LedgerEntry("
            f"id={self.id}, "
            f"debit_account_id={self.debit_account_id}, "
            f"credit_account_id={self.credit_account_id}, "
            f"amount={self.amount}, "
            f"currency={self.currency!r}, "
            f"idempotency_key={self.idempotency_key!r}"
            f")"
        )
