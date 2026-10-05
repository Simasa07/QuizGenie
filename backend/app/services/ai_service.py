import os
import json
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

from app.schemas.quiz import AIQuizResponse, AIQuestion

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
