"""
Integration tests for app/api/quizzes.py. All AI calls are replaced by the
mock_ai_quiz_generation fixture (via generate_quiz), so these run fast,
deterministically, and without needing a real Groq/Gemini key.
"""


class TestGenerateQuiz:
    def test_generates_the_requested_number_of_questions(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=5)
        assert quiz["num_questions"] == 5
        assert len(quiz["questions"]) == 5

    def test_time_limit_is_exactly_what_the_user_chose_not_derived_from_question_count(
        self, client, signup, upload_document, generate_quiz
    ):
        # 20 questions but only 2 minutes - these must be independent choices.
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=20, time_limit_minutes=2)
        assert quiz["time_limit_seconds"] == 2 * 60

    def test_cannot_generate_a_quiz_on_someone_else_s_document(
        self, client, signup, upload_document, mock_ai_quiz_generation
    ):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"], filename="alice_doc.pdf")

        r = client.post(
            "/quizzes/generate",
            headers=bob["headers"],
            json={"document_id": doc["id"], "num_questions": 3, "difficulty": "mixed", "time_limit_minutes": 10},
        )
        assert r.status_code == 404

    def test_cannot_generate_more_than_3_quizzes_per_document(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        generate_quiz(user["headers"], doc["id"])
        generate_quiz(user["headers"], doc["id"])
        generate_quiz(user["headers"], doc["id"])

        r = client.post(
            "/quizzes/generate",
            headers=user["headers"],
            json={"document_id": doc["id"], "num_questions": 3, "difficulty": "mixed", "time_limit_minutes": 10},
        )
        assert r.status_code == 400
        assert "3" in r.json()["detail"]

    def test_quiz_number_increments_across_the_3_allowed_quizzes(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        q1 = generate_quiz(user["headers"], doc["id"])
        q2 = generate_quiz(user["headers"], doc["id"])
        q3 = generate_quiz(user["headers"], doc["id"])
        assert [q1["quiz_number"], q2["quiz_number"], q3["quiz_number"]] == [1, 2, 3]

    def test_31_questions_is_rejected_by_validation(self, client, signup, upload_document, mock_ai_quiz_generation):
        user = signup()
        doc = upload_document(user["headers"])
        r = client.post(
            "/quizzes/generate",
            headers=user["headers"],
            json={"document_id": doc["id"], "num_questions": 31, "difficulty": "mixed", "time_limit_minutes": 10},
        )
        assert r.status_code == 422

    def test_30_questions_is_accepted(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=30)
        assert quiz["num_questions"] == 30

    def test_zero_questions_is_rejected(self, client, signup, upload_document, mock_ai_quiz_generation):
        user = signup()
        doc = upload_document(user["headers"])
        r = client.post(
            "/quizzes/generate",
            headers=user["headers"],
            json={"document_id": doc["id"], "num_questions": 0, "difficulty": "mixed", "time_limit_minutes": 10},
        )
        assert r.status_code == 422


class TestGetQuizAndOwnership:
    def test_owner_can_fetch_their_own_quiz(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"])
        r = client.get(f"/quizzes/{quiz['id']}", headers=user["headers"])
        assert r.status_code == 200

    def test_other_user_cannot_fetch_the_quiz(self, client, signup, upload_document, generate_quiz):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"])
        quiz = generate_quiz(alice["headers"], doc["id"])

        r = client.get(f"/quizzes/{quiz['id']}", headers=bob["headers"])
        assert r.status_code == 404

    def test_other_user_cannot_list_quizzes_for_someone_else_s_document(
        self, client, signup, upload_document, generate_quiz
    ):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        doc = upload_document(alice["headers"])
        generate_quiz(alice["headers"], doc["id"])

        r = client.get(f"/quizzes/document/{doc['id']}", headers=bob["headers"])
        assert r.status_code == 404
