"""
Integration tests for authentication: real HTTP calls through FastAPI's
TestClient against a real (in-memory) database, exercising app/api/users.py
and app/api/deps.py end to end.
"""
from app.database.database import get_db
from tests.conftest import TestingSessionLocal
from app.database import models


class TestSignup:
    def test_signup_succeeds_and_returns_a_token(self, client):
        r = client.post(
            "/users/signup",
            json={"username": "alice", "email": "alice@test.com", "password": "alicepass123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "alice@test.com"
        assert data["username"] == "alice"
        assert "access_token" in data and len(data["access_token"]) > 20

    def test_password_is_hashed_in_the_database_not_plaintext(self, client):
        client.post(
            "/users/signup",
            json={"username": "alice", "email": "alice@test.com", "password": "alicepass123"},
        )
        db = TestingSessionLocal()
        user = db.query(models.User).filter(models.User.email == "alice@test.com").first()
        stored = user.hashed_password
        db.close()

        assert stored != "alicepass123"
        assert stored.startswith("$2b$") or stored.startswith("$2a$")

    def test_duplicate_email_is_rejected(self, client):
        client.post(
            "/users/signup",
            json={"username": "alice", "email": "alice@test.com", "password": "alicepass123"},
        )
        r = client.post(
            "/users/signup",
            json={"username": "someone_else", "email": "alice@test.com", "password": "different"},
        )
        assert r.status_code == 400


class TestLogin:
    def test_correct_credentials_log_in_successfully(self, client, signup):
        signup(email="bob@test.com", password="bobpass123")
        r = client.post("/users/login", json={"email": "bob@test.com", "password": "bobpass123"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_wrong_password_is_rejected(self, client, signup):
        signup(email="bob@test.com", password="bobpass123")
        r = client.post("/users/login", json={"email": "bob@test.com", "password": "wrongpassword"})
        assert r.status_code == 401

    def test_nonexistent_email_is_rejected(self, client):
        r = client.post("/users/login", json={"email": "ghost@test.com", "password": "whatever"})
        assert r.status_code == 401

    def test_wrong_password_and_nonexistent_email_give_the_identical_error(self, client, signup):
        # This matters: if the messages differed, an attacker could use the
        # login endpoint to find out which emails are registered.
        signup(email="bob@test.com", password="bobpass123")
        r1 = client.post("/users/login", json={"email": "bob@test.com", "password": "wrongpassword"})
        r2 = client.post("/users/login", json={"email": "ghost@test.com", "password": "whatever"})
        assert r1.status_code == r2.status_code == 401
        assert r1.json()["detail"] == r2.json()["detail"]


class TestTokenEnforcement:
    def test_protected_endpoint_without_a_token_is_rejected(self, client):
        r = client.get("/documents/mine")
        assert r.status_code == 401

    def test_protected_endpoint_with_a_garbage_token_is_rejected(self, client):
        r = client.get("/documents/mine", headers={"Authorization": "Bearer not-a-real-token"})
        assert r.status_code == 401

    def test_protected_endpoint_with_a_valid_token_succeeds(self, client, signup):
        user = signup()
        r = client.get("/documents/mine", headers=user["headers"])
        assert r.status_code == 200
        assert r.json() == []

    def test_me_endpoint_reflects_the_token_holder(self, client, signup):
        user = signup(email="carol@test.com", username="carol")
        r = client.get("/users/me", headers=user["headers"])
        assert r.status_code == 200
        assert r.json()["email"] == "carol@test.com"
        assert r.json()["username"] == "carol"
