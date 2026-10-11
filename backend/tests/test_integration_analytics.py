"""
Integration tests for app/api/analytics.py: weak-topic math, overview
totals, document scoping, and cross-user isolation. The recommendation
endpoint's AI call is mocked (mock_ai_recommendation) so these tests are
fast and don't need a real API key.
"""


def _complete_quiz_with_pattern(client, headers, quiz, correct_flags):
    """Starts an attempt on `quiz` and submits answers matching correct_flags (list of bool)."""
    r = client.post("/attempts/start", headers=headers, json={"quiz_id": quiz["id"]})
    started = r.json()
    questions = started["quiz"]["questions"]
    answers = [
        {"question_id": q["id"], "selected_option_index": 0 if is_correct else 1}
        for q, is_correct in zip(questions, correct_flags)
    ]
    client.post(f"/attempts/{started['attempt_id']}/submit", headers=headers, json={"answers": answers})


class TestTopicStats:
    def test_no_attempts_yet_gives_an_empty_list(self, client, signup):
        user = signup()
        r = client.get("/analytics/mine/topics", headers=user["headers"])
        assert r.status_code == 200
        assert r.json() == []

    def test_weak_and_strong_topics_are_flagged_correctly(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        # mock cycles topics DHCP, DNS, Subnetting, DHCP for 4 questions
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=4)
        # DHCP: q0 correct, q3 wrong -> 50% (weak)
        # DNS: q1 correct -> 100% (not weak)
        # Subnetting: q2 wrong -> 0% (weak)
        _complete_quiz_with_pattern(client, user["headers"], quiz, [True, True, False, False])

        r = client.get("/analytics/mine/topics", headers=user["headers"])
        stats = {s["topic"]: s for s in r.json()}

        assert stats["DHCP"]["accuracy_percentage"] == 50.0
        assert stats["DHCP"]["is_weak"] is True
        assert stats["DNS"]["accuracy_percentage"] == 100.0
        assert stats["DNS"]["is_weak"] is False
        assert stats["Subnetting"]["accuracy_percentage"] == 0.0
        assert stats["Subnetting"]["is_weak"] is True

    def test_sorted_weakest_first(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=3)
        _complete_quiz_with_pattern(client, user["headers"], quiz, [True, False, False])

        r = client.get("/analytics/mine/topics", headers=user["headers"])
        accuracies = [s["accuracy_percentage"] for s in r.json()]
        assert accuracies == sorted(accuracies)

    def test_other_user_s_topic_stats_are_never_mixed_in(self, client, signup, upload_document, generate_quiz):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")

        alice_doc = upload_document(alice["headers"], filename="alice.pdf")
        alice_quiz = generate_quiz(alice["headers"], alice_doc["id"], num_questions=1)
        _complete_quiz_with_pattern(client, alice["headers"], alice_quiz, [False])  # Alice gets it wrong

        bob_doc = upload_document(bob["headers"], filename="bob.pdf")
        bob_quiz = generate_quiz(bob["headers"], bob_doc["id"], num_questions=1)
        _complete_quiz_with_pattern(client, bob["headers"], bob_quiz, [True])  # Bob gets it right

        bob_stats = client.get("/analytics/mine/topics", headers=bob["headers"]).json()
        # Bob's own topic (same name, "DHCP") must show HIS 100%, not be
        # polluted by Alice's wrong answer on her own separate attempt.
        assert bob_stats[0]["accuracy_percentage"] == 100.0

    def test_querying_someone_else_s_document_id_returns_empty_not_their_data(
        self, client, signup, upload_document, generate_quiz
    ):
        alice = signup(email="alice@test.com")
        bob = signup(email="bob@test.com")
        alice_doc = upload_document(alice["headers"], filename="alice.pdf")
        alice_quiz = generate_quiz(alice["headers"], alice_doc["id"], num_questions=1)
        _complete_quiz_with_pattern(client, alice["headers"], alice_quiz, [True])

        # Bob passes Alice's document_id as a filter - must not leak her data.
        r = client.get("/analytics/mine/topics", headers=bob["headers"], params={"document_id": alice_doc["id"]})
        assert r.status_code == 200
        assert r.json() == []


class TestOverview:
    def test_totals_add_up_across_multiple_attempts(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"])
        quiz1 = generate_quiz(user["headers"], doc["id"], num_questions=2)
        _complete_quiz_with_pattern(client, user["headers"], quiz1, [True, False])  # 1/2

        r = client.get("/analytics/mine/overview", headers=user["headers"])
        data = r.json()
        assert data["total_attempts"] == 1
        assert data["total_questions_answered"] == 2
        assert data["total_correct"] == 1
        assert data["overall_accuracy_percentage"] == 50.0

    def test_recent_attempts_includes_document_filename(self, client, signup, upload_document, generate_quiz):
        user = signup()
        doc = upload_document(user["headers"], filename="networking.pdf")
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=1)
        _complete_quiz_with_pattern(client, user["headers"], quiz, [True])

        r = client.get("/analytics/mine/overview", headers=user["headers"])
        assert r.json()["recent_attempts"][0]["document_filename"] == "networking.pdf"


class TestRecommendation:
    def test_no_data_yet_gives_a_friendly_fallback_without_calling_ai(self, client, signup):
        user = signup()
        r = client.get("/analytics/mine/recommendation", headers=user["headers"])
        assert r.status_code == 200
        assert r.json()["weak_topics"] == []
        assert "take a quiz" in r.json()["recommendation"].lower()

    def test_with_data_calls_the_mocked_ai_and_returns_weak_topics(
        self, client, signup, upload_document, generate_quiz, mock_ai_recommendation
    ):
        user = signup()
        doc = upload_document(user["headers"])
        quiz = generate_quiz(user["headers"], doc["id"], num_questions=3)
        _complete_quiz_with_pattern(client, user["headers"], quiz, [False, True, True])

        r = client.get("/analytics/mine/recommendation", headers=user["headers"])
        assert r.status_code == 200
        assert "DHCP" in r.json()["recommendation"]  # the weakest topic (question 0)
        assert "DHCP" in r.json()["weak_topics"]
