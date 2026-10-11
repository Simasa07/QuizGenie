"""
Unit tests for generate_study_recommendation() in app/services/ai_service.py.

The real AI client is replaced by a tiny fake, so these run instantly with no
network and no API key - and they can check things a live call never could,
like exactly what token ceiling and prompt were sent.
"""
from types import SimpleNamespace

import pytest

from app.schemas.quiz import TopicStat
from app.services import ai_service
from app.services.ai_service import (
    AIServiceError,
    RECOMMENDATION_MAX_TOKENS,
    RECOMMENDATION_MAX_WORDS,
    _drop_dangling_fragment,
    generate_study_recommendation,
)


def make_stats():
    # Already weakest-first, as the analytics endpoint supplies them.
    return [
        TopicStat(topic="Subnetting", total_answered=4, correct=1, accuracy_percentage=25.0, is_weak=True),
        TopicStat(topic="VLANs", total_answered=4, correct=4, accuracy_percentage=100.0, is_weak=False),
    ]


class FakeClient:
    """Stands in for the OpenAI client; records what it was asked and returns a canned reply."""

    def __init__(self, content="Focus on Subnetting first.", finish_reason="stop", raises=None):
        self.calls = []
        self._content = content
        self._finish_reason = finish_reason
        self._raises = raises
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises:
            raise self._raises
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=self._finish_reason)])


@pytest.fixture
def use_client(monkeypatch):
    def _use(**kwargs):
        fake = FakeClient(**kwargs)
        monkeypatch.setattr(ai_service, "client", fake)
        return fake

    return _use


class TestRequestSentToTheModel:
    def test_uses_the_configured_token_ceiling(self, use_client):
        fake = use_client()
        generate_study_recommendation(make_stats())
        assert fake.calls[0]["max_tokens"] == RECOMMENDATION_MAX_TOKENS

    def test_token_ceiling_leaves_generous_headroom_over_the_word_limit(self):
        # This is the regression guard for the "tip stops halfway through a
        # sentence" bug: the ceiling must be far above what the word limit
        # needs (roughly 1.5 tokens per word), not right at the edge of it.
        assert RECOMMENDATION_MAX_TOKENS >= RECOMMENDATION_MAX_WORDS * 4

    def test_prompt_tells_the_model_the_word_limit(self, use_client):
        fake = use_client()
        generate_study_recommendation(make_stats())
        sent = " ".join(m["content"] for m in fake.calls[0]["messages"])
        assert f"under {RECOMMENDATION_MAX_WORDS} words" in sent

    def test_prompt_names_the_weakest_topic_explicitly(self, use_client):
        fake = use_client()
        generate_study_recommendation(make_stats())
        user_message = fake.calls[0]["messages"][1]["content"]
        assert "The weakest topic is 'Subnetting' at 25.0%" in user_message

    def test_every_topic_with_its_accuracy_is_included(self, use_client):
        fake = use_client()
        generate_study_recommendation(make_stats())
        user_message = fake.calls[0]["messages"][1]["content"]
        assert "Subnetting: 25.0% (1/4 correct)" in user_message
        assert "VLANs: 100.0% (4/4 correct)" in user_message


class TestReplyHandling:
    def test_a_complete_reply_is_returned_as_is(self, use_client):
        use_client(content="Revisit Subnetting masks first. Then practise five VLSM questions.", finish_reason="stop")
        text = generate_study_recommendation(make_stats())
        assert text == "Revisit Subnetting masks first. Then practise five VLSM questions."

    def test_surrounding_whitespace_is_stripped(self, use_client):
        use_client(content="  \n Focus on Subnetting.  \n")
        assert generate_study_recommendation(make_stats()) == "Focus on Subnetting."

    def test_a_reply_cut_off_at_the_ceiling_is_trimmed_to_the_last_full_sentence(self, use_client):
        use_client(
            content="Focus on Subnetting first. Practise host calculations daily. Then re-do the mixed set and che",
            finish_reason="length",
        )
        text = generate_study_recommendation(make_stats())
        assert text == "Focus on Subnetting first. Practise host calculations daily."

    def test_a_cut_off_reply_never_ends_mid_sentence(self, use_client):
        use_client(content="Focus on Subnetting. Practise the next th", finish_reason="length")
        assert generate_study_recommendation(make_stats())[-1] in ".!?"

    def test_a_clean_reply_is_not_trimmed_even_if_flagged_length(self, use_client):
        use_client(content="Focus on Subnetting first.", finish_reason="length")
        assert generate_study_recommendation(make_stats()) == "Focus on Subnetting first."


class TestFailureHandling:
    def test_empty_reply_raises_a_clear_error(self, use_client):
        use_client(content="")
        with pytest.raises(AIServiceError):
            generate_study_recommendation(make_stats())

    def test_none_reply_raises_a_clear_error(self, use_client):
        use_client(content=None)
        with pytest.raises(AIServiceError):
            generate_study_recommendation(make_stats())

    def test_api_failure_is_wrapped_in_aiserviceerror(self, use_client):
        use_client(raises=RuntimeError("429 quota exceeded"))
        with pytest.raises(AIServiceError) as exc_info:
            generate_study_recommendation(make_stats())
        assert "429 quota exceeded" in str(exc_info.value)


class TestDropDanglingFragment:
    def test_complete_text_is_unchanged(self):
        assert _drop_dangling_fragment("All done.") == "All done."
        assert _drop_dangling_fragment("Really?") == "Really?"
        assert _drop_dangling_fragment("Great!") == "Great!"

    def test_trailing_fragment_is_removed(self):
        assert _drop_dangling_fragment("First. Second. Thi") == "First. Second."

    def test_closing_quote_after_full_stop_counts_as_complete(self):
        assert _drop_dangling_fragment('He said "stop."') == 'He said "stop."'

    def test_single_unfinished_sentence_is_left_alone_rather_than_emptied(self):
        # Nothing complete to fall back to - better a fragment than nothing.
        assert _drop_dangling_fragment("Focus on Subnet") == "Focus on Subnet"

    def test_empty_input_stays_empty(self):
        assert _drop_dangling_fragment("") == ""
        assert _drop_dangling_fragment("   ") == ""
