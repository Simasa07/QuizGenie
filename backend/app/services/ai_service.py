import os
import json
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

from app.schemas.quiz import AIQuizResponse, AIQuestion, TopicStat

load_dotenv()

client = OpenAI(
    api_key=os.getenv("AI_API_KEY"),
    base_url=os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1"),
)
MODEL_NAME = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")

BASE_SYSTEM_PROMPT = """You are an expert exam question writer. You generate multiple-choice
questions STRICTLY based on the study material the user provides.

Rules:
- Do not invent facts that are not supported by the source material.
- Each question must have exactly 4 options and exactly ONE correct option.
- Avoid ambiguous wording and avoid questions with more than one plausible correct answer.
- Avoid duplicate or near-duplicate questions - vary phrasing and the concept tested
  across the set, don't just reword the same fact repeatedly.
- Distractors (wrong options) must be plausible, not silly or obviously wrong.
- Assign a short topic label and a difficulty level ("easy", "medium", or "hard") to each question.
- Respond with ONLY valid JSON matching this exact schema, no markdown fences, no commentary:

{
  "questions": [
    {
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_option": 0,
      "explanation": "string",
      "topic": "string",
      "difficulty": "easy|medium|hard"
    }
  ]
}
"""

# V2: difficulty-specific guidance appended to the base prompt.
DIFFICULTY_INSTRUCTIONS = {
    "easy": "Focus on direct recall of definitions and basic facts stated plainly in the material. Keep difficulty \"easy\" for every question.",
    "medium": "Focus on understanding and applying concepts, not just recalling definitions. Keep difficulty \"medium\" for every question.",
    "hard": "Focus on multi-step reasoning, edge cases, and distinguishing closely related concepts from the material. Keep difficulty \"hard\" for every question.",
    "mixed": "Spread the questions across difficulty levels: roughly a third easy (recall), a third medium (application), and a third hard (multi-step reasoning or fine distinctions).",
}


def build_system_prompt(difficulty: str) -> str:
    instruction = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["mixed"])
    return BASE_SYSTEM_PROMPT + f"\nDifficulty guidance for this quiz: {instruction}\n"


def build_user_prompt(content_chunks: List[str], num_questions: int) -> str:
    joined_content = "\n\n---\n\n".join(content_chunks)
    return (
        f"Study material:\n\n{joined_content}\n\n"
        f"Generate exactly {num_questions} multiple-choice questions based only on "
        f"the study material above."
    )


class AIServiceError(Exception):
    """Raised when the AI call or its response can't be turned into valid questions."""


def generate_quiz_questions(
    content_chunks: List[str],
    num_questions: int,
    difficulty: str = "mixed",
) -> List[AIQuestion]:
    """Call the AI model, parse its structured JSON output, and validate it."""
    if not content_chunks:
        raise AIServiceError("No extracted text available for this document.")

    system_prompt = build_system_prompt(difficulty)
    user_prompt = build_user_prompt(content_chunks, num_questions)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
    except Exception as exc:
        raise AIServiceError(
            f"AI API call failed ({os.getenv('AI_BASE_URL', 'https://api.groq.com/openai/v1')}, model={MODEL_NAME}): {exc}"
        ) from exc

    raw_content = response.choices[0].message.content or ""

    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        parsed = AIQuizResponse(**data)
    except Exception as exc:
        raise AIServiceError(f"Could not parse AI response as valid JSON: {exc}") from exc

    return validate_and_filter(parsed.questions)


def _word_set(text: str) -> set:
    """Lowercase, punctuation-stripped word set used for a cheap similarity check."""
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text)
    return {w for w in cleaned.split() if len(w) > 2}  # drop tiny words like "a", "is"


def _jaccard_similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def validate_and_filter(questions: List[AIQuestion]) -> List[AIQuestion]:
    """
    V2 validation pass:
    - exactly 4 options
    - correct_option index is in range
    - drop exact-duplicate question text (case-insensitive)
    - drop near-duplicate questions using word-overlap similarity (catches
      reworded repeats like "What does DHCP do?" vs "What is the purpose
      of DHCP?" without needing an embeddings call)
    """
    NEAR_DUPLICATE_THRESHOLD = 0.6  # fraction of shared significant words

    seen_texts = set()
    seen_word_sets: List[set] = []
    valid_questions: List[AIQuestion] = []

    for q in questions:
        normalized = q.question.strip().lower()

        if len(q.options) != 4:
            continue
        if not (0 <= q.correct_option < 4):
            continue
        if normalized in seen_texts:
            continue

        word_set = _word_set(q.question)
        is_near_duplicate = any(
            _jaccard_similarity(word_set, existing) >= NEAR_DUPLICATE_THRESHOLD
            for existing in seen_word_sets
        )
        if is_near_duplicate:
            continue

        seen_texts.add(normalized)
        seen_word_sets.append(word_set)
        valid_questions.append(q)

    return valid_questions


# --- Study-tip length: the two settings to change, all in one place ----------
# RECOMMENDATION_MAX_WORDS is what the prompt TELLS the model to stay under -
# this is what actually controls how long a tip is.
# RECOMMENDATION_MAX_TOKENS is only a safety ceiling enforced by the API (you
# are billed for tokens actually produced, not for the ceiling). Keep it far
# above the word limit: one word is roughly 1.3-1.5 tokens, and some models
# spend part of this budget "thinking" before they answer - a ceiling that is
# too low is exactly what makes a tip stop halfway through a sentence.
RECOMMENDATION_MAX_WORDS = 160
RECOMMENDATION_MAX_TOKENS = 2000

RECOMMENDATION_SYSTEM_PROMPT = f"""You are a supportive, practical study coach. Given a student's
accuracy breakdown by topic, write a personalized study recommendation.

Rules:
- Keep the ENTIRE reply under {RECOMMENDATION_MAX_WORDS} words. This is a hard limit - never let it get
  cut off mid-sentence, so finish comfortably within it rather than right at the edge.
- 4 to 6 sentences of plain text. No markdown, no bullet points, no headers, no numbered lists.
- ALWAYS lead with the single weakest topic by its exact label and give specific, actionable
  advice on how to improve at it: what to revisit first, how to practise it, and how they can
  check they have improved. This is the most important part of the reply - do not open with
  praise or with a strong topic.
- If other topics are also weak, mention them briefly afterwards, weakest first.
- You may acknowledge a strength in one short clause, but only after the advice about the weak
  topic(s), never before it, and only if there genuinely is a strong topic.
- Be specific and actionable, not generic ("keep practicing" alone is not useful).
- Do not invent topics that are not in the data given to you.
"""


def _drop_dangling_fragment(text: str) -> str:
    """
    Safety net for a reply the API cut off at its token ceiling: drop the
    unfinished last sentence so the student never sees half a sentence.
    A reply that already ends cleanly is returned unchanged.
    """
    stripped = text.strip()
    core = stripped.rstrip("\"')")  # a closing quote/bracket after the full stop still counts
    if not core or core[-1] in ".!?":
        return stripped
    last_end = max(stripped.rfind("."), stripped.rfind("!"), stripped.rfind("?"))
    # Only trim if at least one complete sentence exists before the fragment.
    return stripped[: last_end + 1] if last_end > 0 else stripped


def generate_study_recommendation(topic_stats: List[TopicStat]) -> str:
    """
    V4: turns a topic accuracy breakdown into a short, encouraging,
    actionable study recommendation. Plain-text completion (not JSON
    mode) since the output is prose, not structured data.
    """
    breakdown_lines = [
        f"- {s.topic}: {s.accuracy_percentage}% ({s.correct}/{s.total_answered} correct)"
        for s in topic_stats
    ]

    # topic_stats is already sorted weakest-first by the caller - naming the
    # weakest topic explicitly removes any ambiguity for the model, rather
    # than leaving it to infer which one is "weakest" from a list.
    weakest = topic_stats[0]

    user_prompt = (
        "Topic accuracy breakdown (weakest first):\n" + "\n".join(breakdown_lines) +
        f"\n\nThe weakest topic is '{weakest.topic}' at {weakest.accuracy_percentage}%. "
        f"Lead your recommendation with this topic and concrete advice for it. "
        f"Write the study recommendation now, under {RECOMMENDATION_MAX_WORDS} words total."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=RECOMMENDATION_MAX_TOKENS,
        )
    except Exception as exc:
        raise AIServiceError(
            f"AI API call failed ({os.getenv('AI_BASE_URL', 'https://api.groq.com/openai/v1')}, model={MODEL_NAME}): {exc}"
        ) from exc

    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    if not text:
        raise AIServiceError("AI returned an empty recommendation.")

    # finish_reason == "length" means the API stopped at the token ceiling
    # rather than because the model finished - trim any dangling fragment.
    if getattr(choice, "finish_reason", None) == "length":
        text = _drop_dangling_fragment(text)
    return text
