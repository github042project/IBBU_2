"""Pytest configuration and fixtures for IB Wallet tests."""

import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

# Add project root to sys.path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import models to register them with Base
from models.account import Base, Account
from models.ledger_entry import LedgerEntry
from db.session import get_db


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a shared in-memory SQLite database for testing.
    
    Uses URI mode with cache=shared to allow multiple connections
    to access the same in-memory database.
    """
    # Use shared in-memory database so all connections see same data
    engine = create_engine(
        "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        future=True,
    )
    # Create all tables
    Base.metadata.create_all(engine)
    yield engine
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Iterator[Session]:
    """Create a test database session."""
    TestSessionLocal = sessionmaker(
        bind=test_db_engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_app(test_db_session: Session):
    """Create a FastAPI test app with database dependency overridden."""
    from main import app as fastapi_app

    # Override the get_db dependency to use test session
    def override_get_db() -> Iterator[Session]:
        yield test_db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    client = TestClient(fastapi_app)
    try:
        yield client
    finally:
        client.close()
        fastapi_app.dependency_overrides.pop(get_db, None)
