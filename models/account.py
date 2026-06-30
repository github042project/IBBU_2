"""
Models for IB Wallet - Account module.

Provides SQLAlchemy 2.0 models for representing user accounts.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class AccountType(str, Enum):
    """
    Enumeration for account types.
    
    Defines the types of accounts available in IB Wallet.
    
    Attributes:
        BALANCE: Regular account for storing current balance
        POT: Savings pot account with optional target amount
    """
    BALANCE = "balance"
    POT = "pot"


class Account(Base):
    """
    Represents a user account in IB Wallet.
    
    An account can be either a regular balance account or a savings pot.
    Each account is associated with a specific user and currency, and tracks
    the current balance along with an optional target amount for pot accounts.
    
    Accounts can be closed, which is tracked via the closed_at timestamp.
    
    Attributes:
        id: Unique account identifier (primary key)
        user_id: Foreign key reference to the user who owns this account
        account_type: Type of account (BALANCE or POT)
        currency: ISO 4217 currency code (e.g., INR, CHF)
        name: Human-readable name for the account
        balance: Current balance stored as Decimal for precision
        target_amount: Optional target amount for POT accounts
        created_at: Timestamp when the account was created (UTC)
        closed_at: Optional timestamp when the account was closed (UTC)
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Unique account identifier."""

    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    """Foreign key to the user who owns this account."""

    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType), nullable=False
    )
    """Type of account: BALANCE or POT."""

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    """ISO 4217 currency code (e.g., INR, CHF)."""

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Human-readable name for the account."""

    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=2), nullable=False
    )
    """Current account balance stored as Decimal for financial precision."""

    target_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=19, scale=2), nullable=True
    )
    """Optional target amount for POT accounts."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    """Timestamp when the account was created (UTC)."""

    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """Optional timestamp when the account was closed (UTC)."""

    def __repr__(self) -> str:
        """
        Return string representation of the Account.
        
        Returns:
            A detailed string representation including key account details.
        """
        return (
            f"Account("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"account_type={self.account_type}, "
            f"currency={self.currency}, "
            f"name={self.name!r}, "
            f"balance={self.balance}"
            f")"
        )

    def is_open(self) -> bool:
        """
        Check if the account is currently open.
        
        Returns:
            True if the account has not been closed, False otherwise.
        """
        return self.closed_at is None

    def is_closed(self) -> bool:
        """
        Check if the account is closed.
        
        Returns:
            True if the account has been closed, False otherwise.
        """
        return self.closed_at is not None
