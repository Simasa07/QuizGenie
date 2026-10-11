def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_signup_fixture_works(signup):
    user = signup(email="smoke@test.com")
    assert user["id"] > 0
    assert user["headers"]["Authorization"].startswith("Bearer ")
