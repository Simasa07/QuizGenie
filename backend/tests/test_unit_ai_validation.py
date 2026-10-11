"""
Unit tests for the pure validation/filtering logic in app/services/ai_service.py.
These never call the real AI - they test validate_and_filter() directly
against hand-built AIQuestion objects, so they run instantly and need no
network access or API key.
"""
from app.schemas.quiz import AIQuestion
from app.services.ai_service import validate_and_filter, _word_set, _jaccard_similarity


def make_question(text="Sample question?", correct=0, topic="General", difficulty="easy"):
    return AIQuestion(
        question=text,
        options=["A", "B", "C", "D"],
        correct_option=correct,
        explanation="Because.",
        topic=topic,
        difficulty=difficulty,
    )


class TestOptionCountValidation:
    def test_question_with_exactly_4_options_is_kept(self):
        q = make_question()
        assert validate_and_filter([q]) == [q]

    def test_question_with_3_options_is_dropped(self):
        q = make_question()
        q.options = ["A", "B", "C"]
        assert validate_and_filter([q]) == []

    def test_question_with_5_options_is_dropped(self):
        q = make_question()
        q.options = ["A", "B", "C", "D", "E"]
        assert validate_and_filter([q]) == []


class TestCorrectOptionRangeValidation:
    def test_correct_option_in_range_is_kept(self):
        for i in range(4):
            q = make_question(text=f"Question {i}?", correct=i)
            assert validate_and_filter([q]) == [q]

    def test_negative_correct_option_is_dropped(self):
        q = make_question(correct=-1)
        assert validate_and_filter([q]) == []

    def test_correct_option_out_of_range_is_dropped(self):
        q = make_question(correct=4)
        assert validate_and_filter([q]) == []


class TestExactDuplicateDetection:
    def test_identical_question_text_keeps_only_the_first(self):
        q1 = make_question(text="What does DHCP do?")
        q2 = make_question(text="What does DHCP do?")
        result = validate_and_filter([q1, q2])
        assert result == [q1]

    def test_case_insensitive_duplicate_is_still_caught(self):
        q1 = make_question(text="What does DHCP do?")
        q2 = make_question(text="WHAT DOES DHCP DO?")
        result = validate_and_filter([q1, q2])
        assert len(result) == 1

    def test_different_questions_both_kept(self):
        q1 = make_question(text="What does DHCP do?")
        q2 = make_question(text="What does DNS do?")
        result = validate_and_filter([q1, q2])
        assert len(result) == 2


class TestNearDuplicateDetection:
    def test_reworded_question_about_the_same_fact_is_caught(self):
        q1 = make_question(text="What is the purpose of DHCP in a network?")
        q2 = make_question(text="What is the main purpose of DHCP on a network?")
        result = validate_and_filter([q1, q2])
        assert len(result) == 1

    def test_genuinely_different_questions_both_survive(self):
        q1 = make_question(text="What is the purpose of DHCP in a network?")
        q2 = make_question(text="Which protocol translates domain names into IP addresses?")
        result = validate_and_filter([q1, q2])
        assert len(result) == 2


class TestWordSetHelper:
    def test_strips_punctuation_and_lowercases(self):
        words = _word_set("What is DHCP's purpose?")
        assert "what" in words
        assert "dhcp" in words or "dhcps" in words  # apostrophe handling

    def test_drops_short_words(self):
        words = _word_set("Is it a DNS or an IP?")
        assert "is" not in words  # 2 chars
        assert "it" not in words  # 2 chars
        assert "dns" in words


class TestJaccardSimilarity:
    def test_identical_sets_have_similarity_1(self):
        s = {"dhcp", "network", "purpose"}
        assert _jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets_have_similarity_0(self):
        a = {"dhcp", "network"}
        b = {"completely", "different", "words"}
        assert _jaccard_similarity(a, b) == 0.0

    def test_empty_set_gives_zero_not_a_crash(self):
        assert _jaccard_similarity(set(), {"a"}) == 0.0
        assert _jaccard_similarity(set(), set()) == 0.0
