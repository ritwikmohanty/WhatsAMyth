"""
Pytest Configuration and Fixtures
"""

import os
import pytest
from typing import Generator

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["FAISS_INDEX_PATH"] = "/tmp/test_faiss.index"
os.environ["MEMORY_GRAPH_PATH"] = "/tmp/test_graph.json"
os.environ["TTS_PROVIDER"] = "pyttsx3"
os.environ["LLM_BACKEND"] = "fallback"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models import Base
from app.db import get_db
from app.main import app


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator:
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db) -> Generator:
    """Create test client with fresh database."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_claim():
    """Sample claim text for testing."""
    return "Scientists have discovered that drinking warm water kills coronavirus instantly."


@pytest.fixture
def sample_non_claim():
    """Sample non-claim text for testing."""
    return "Hello, how are you doing today?"


@pytest.fixture
def sample_claims_batch():
    """Batch of sample claims for testing clustering."""
    return [
        "Drinking warm water kills coronavirus",
        "Hot water can cure COVID-19 infection",
        "Warm water destroys the coronavirus",
        "5G towers cause COVID-19",
        "5G radiation spreads coronavirus",
    ]
