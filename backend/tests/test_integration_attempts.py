"""
Integration tests for app/api/attempts.py: starting, submitting, scoring,
and - critically - that attempts can't be started or read by anyone other
than the user who owns the underlying quiz/document.
"""


def _start(client, headers, quiz_id):
    r = client.post("/attempts/start", headers=headers, json={"quiz_id": quiz_id})
    assert r.status_code == 200, r.text
    return r.json()


class TestStartAttempt:
    def test_start_attempt_succeeds_for_the_quiz_owner(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=3)
        result = _start(client, user["headers"], quiz["id"])
        assert "attempt_id" in result
        assert result["quiz"]["id"] == quiz["id"]

    def test_cannot_start_an_attempt_on_someone_else_s_quiz(self, client, signup, upload_document, generate_quiz):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"])
        quiz = generate_quiz(alice["headers"], doc["id"])

        r = client.post("/attempts/start", headers=bob["headers"], json={"quiz_id": quiz["id"]})
        assert r.status_code == 404

    def test_body_no_longer_accepts_a_user_id_field(self, client, signup, upload_document, generate_quiz):
        # Confirms the old insecure "trust whatever user_id the client sends"
        # field is really gone - passing it should simply be ignored, not
        # used to impersonate someone.
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"])
        quiz = generate_quiz(alice["headers"], doc["id"])

        r = client.post(
            "/attempts/start",
            headers=alice["headers"],
            json={"quiz_id": quiz["id"], "user_id": bob["id"]},  # extra field, should be ignored
        )
        assert r.status_code == 200
        # The attempt must belong to Alice (the token holder), not Bob.
        attempt_id = r.json()["attempt_id"]
        detail = client.get(f"/attempts/{attempt_id}", headers=bob["headers"])
        assert detail.status_code == 404  # Bob still can't see it


class TestSubmitAndScoring:
    def test_all_correct_answers_scores_100_percent(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=3)
        started = _start(client, user["headers"], quiz["id"])

        # The fixture always makes option_index 0 correct.
        answers = [{"question_id": q["id"], "selected_option_index": 0} for q in started["quiz"]["questions"]]
        r = client.post(
            f"/attempts/{started['attempt_id']}/submit", headers=user["headers"], json={"answers": answers}
        )
        assert r.status_code == 200
        result = r.json()
        assert result["score"] == 3
        assert result["total_questions"] == 3
        assert result["percentage"] == 100.0

    def test_all_wrong_answers_scores_0_percent(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=3)
        started = _start(client, user["headers"], quiz["id"])

        answers = [{"question_id": q["id"], "selected_option_index": 1} for q in started["quiz"]["questions"]]
        r = client.post(
            f"/attempts/{started['attempt_id']}/submit", headers=user["headers"], json={"answers": answers}
        )
        assert r.json()["score"] == 0
        assert r.json()["percentage"] == 0.0

    def test_mixed_answers_score_correctly(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=4)
        started = _start(client, user["headers"], quiz["id"])

        questions = started["quiz"]["questions"]
        answers = [
            {"question_id": questions[0]["id"], "selected_option_index": 0},  # correct
            {"question_id": questions[1]["id"], "selected_option_index": 0},  # correct
            {"question_id": questions[2]["id"], "selected_option_index": 1},  # wrong
            {"question_id": questions[3]["id"], "selected_option_index": 1},  # wrong
        ]
        r = client.post(
            f"/attempts/{started['attempt_id']}/submit", headers=user["headers"], json={"answers": answers}
        )
        assert r.json()["score"] == 2
        assert r.json()["percentage"] == 50.0

    def test_cannot_submit_the_same_attempt_twice(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=2)
        started = _start(client, user["headers"], quiz["id"])
        answers = [{"question_id": q["id"], "selected_option_index": 0} for q in started["quiz"]["questions"]]

        client.post(f"/attempts/{started['attempt_id']}/submit", headers=user["headers"], json={"answers": answers})
        r2 = client.post(f"/attempts/{started['attempt_id']}/submit", headers=user["headers"], json={"answers": answers})
        assert r2.status_code == 400

    def test_cannot_submit_someone_else_s_attempt(self, client, signup, upload_document, generate_quiz):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"])
        quiz = generate_quiz(alice["headers"], doc["id"], num_questions=2)
        started = _start(client, alice["headers"], quiz["id"])

        answers = [{"question_id": q["id"], "selected_option_index": 0} for q in started["quiz"]["questions"]]
        r = client.post(
            f"/attempts/{started['attempt_id']}/submit", headers=bob["headers"], json={"answers": answers}
        )
        assert r.status_code == 404


class TestHistory:
    def test_history_shows_only_the_caller_s_own_attempts(self, client, signup, upload_document, generate_quiz):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")

        alice_doc = upload_document(alice["headers"], filename="alice.pdf")
        alice_quiz = generate_quiz(alice["headers"], alice_doc["id"], num_questions=1)
        alice_started = _start(client, alice["headers"], alice_quiz["id"])
        client.post(
            f"/attempts/{alice_started['attempt_id']}/submit",
            headers=alice["headers"],
            json={"answers": [{"question_id": alice_started["quiz"]["questions"][0]["id"], "selected_option_index": 0}]},
        )

        bob_doc = upload_document(bob["headers"], filename="bob.pdf")
        bob_quiz = generate_quiz(bob["headers"], bob_doc["id"], num_questions=1)
        _start(client, bob["headers"], bob_quiz["id"])  # Bob starts but does not submit

        r = client.get("/attempts/mine", headers=alice["headers"])
        results = r.json()
        assert len(results) == 1
        assert results[0]["document_filename"] == "alice.pdf"
