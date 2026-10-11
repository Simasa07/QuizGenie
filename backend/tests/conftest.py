import os

# Must be set BEFORE importing anything under app/, since database.py reads
# DATABASE_URL at import time when it builds the real engine.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AI_API_KEY", "test-dummy-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-not-for-production")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import Base, get_db

# A single shared in-memory SQLite DB for the whole test run, isolated from
# whatever the app's own database.py connected to at import time (that one
# is never queried by these tests - get_db is fully overridden below).
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test gets a clean schema - no leftover rows from a previous test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def signup(client):
    """
    signup() -> dict with headers/id/token for a fresh, ready-to-use account.
    Call it multiple times with different emails to get multiple distinct users
    (e.g. for cross-user isolation tests).
    """

    def _signup(email="user@test.com", password="password123", username="testuser"):
        r = client.post(
            "/users/signup",
            json={"username": username, "email": email, "password": password},
        )
        assert r.status_code == 200, f"signup fixture failed: {r.status_code} {r.text}"
        data = r.json()
        return {
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "id": data["id"],
            "token": data["access_token"],
            "email": email,
            "password": password,
        }

    return _signup


@pytest.fixture
def sample_pdf_bytes():
    """A tiny real PDF with extractable text, built in-memory with PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "DHCP automatically assigns IP addresses to devices on a network. "
        "DNS resolves domain names to IP addresses. "
        "Subnetting divides a network into smaller logical networks.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def upload_document(client, sample_pdf_bytes):
    """
    upload_document(headers, filename="sample.pdf") -> the DocumentOut dict.
    Uploads sample_pdf_bytes as the given user and asserts it processed OK.
    """

    def _upload(headers, filename="sample.pdf"):
        r = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": (filename, sample_pdf_bytes, "application/pdf")},
        )
        assert r.status_code == 200, f"upload_document fixture failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["status"] == "processed"
        return data

    return _upload


@pytest.fixture
def mock_ai_quiz_generation(monkeypatch):
    """
    Replaces the real AI call with a fast, deterministic fake so quiz-generation
    tests don't need network access or an API key, and don't burn real quota.
    Generates distinct, non-duplicate questions cycling through a few topics,
    so both quiz-count tests and topic-analytics tests have realistic data.
    """
    from app.schemas.quiz import AIQuestion

    topics = ["DHCP", "DNS", "Subnetting"]

    def _fake_generate(chunks, num_questions, difficulty="mixed"):
        return [
            AIQuestion(
                question=f"Fake question #{i} about {topics[i % len(topics)]}?",
                options=["Correct answer", "Wrong A", "Wrong B", "Wrong C"],
                correct_option=0,
                explanation="Because the fixture says so.",
                topic=topics[i % len(topics)],
                difficulty=difficulty if difficulty != "mixed" else "medium",
            )
            for i in range(num_questions)
        ]

    monkeypatch.setattr("app.api.quizzes.generate_quiz_questions", _fake_generate)
    return _fake_generate


@pytest.fixture
def generate_quiz(client, mock_ai_quiz_generation):
    """
    generate_quiz(headers, document_id, num_questions=3, **kwargs) -> QuizOut dict.
    Requires mock_ai_quiz_generation so no real AI call happens.
    """

    def _generate(headers, document_id, num_questions=3, difficulty="mixed", time_limit_minutes=10):
        r = client.post(
            "/quizzes/generate",
            headers=headers,
            json={
                "document_id": document_id,
                "num_questions": num_questions,
                "difficulty": difficulty,
                "time_limit_minutes": time_limit_minutes,
            },
        )
        assert r.status_code == 200, f"generate_quiz fixture failed: {r.status_code} {r.text}"
        return r.json()

    return _generate


@pytest.fixture
def mock_ai_recommendation(monkeypatch):
    """Replaces the real AI call behind /analytics/mine/recommendation with a fixed string."""

    def _fake_recommendation(topic_stats):
        weakest = topic_stats[0]
        return f"Focus on {weakest.topic} - fake recommendation from the test fixture."

    monkeypatch.setattr("app.api.analytics.generate_study_recommendation", _fake_recommendation)
    return _fake_recommendation
