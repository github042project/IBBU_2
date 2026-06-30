"""
Database session configuration for IB Wallet.

Provides the SQLAlchemy engine, session factory, and dependency injection helper.
Uses SQLite for local development and is ready to switch to PostgreSQL via DATABASE_URL.
"""

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ib_wallet.db")

ENGINE_ARGS = {
    "future": True,
    "echo": False,
}

if DATABASE_URL.startswith("sqlite"):
    ENGINE_ARGS["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **ENGINE_ARGS)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Iterator[Session]:
    """Provide a transactional database session for request handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
