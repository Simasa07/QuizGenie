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

SYSTEM_PROMPT = """You are an expert exam question writer. You generate multiple-choice
questions STRICTLY based on the study material the user provides.

Rules:
- Do not invent facts that are not supported by the source material.
- Each question must have exactly 4 options and exactly ONE correct option.
- Avoid ambiguous wording and avoid questions with more than one plausible correct answer.
- Avoid duplicate or near-duplicate questions.
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


def build_user_prompt(content_chunks: List[str], num_questions: int) -> str:
    joined_content = "\n\n---\n\n".join(content_chunks)
    return (
        f"Study material:\n\n{joined_content}\n\n"
        f"Generate exactly {num_questions} multiple-choice questions based only on "
        f"the study material above."
    )


class AIServiceError(Exception):
    """Raised when the AI call or its response can't be turned into valid questions."""


def generate_quiz_questions(content_chunks: List[str], num_questions: int) -> List[AIQuestion]:
    """Call the AI model, parse its structured JSON output, and validate it."""
    if not content_chunks:
        raise AIServiceError("No extracted text available for this document.")

    user_prompt = build_user_prompt(content_chunks, num_questions)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
    except Exception as exc:
        # Covers auth errors, rate limits, network issues, bad model name, etc.
        raise AIServiceError(f"AI API call failed ({os.getenv('AI_BASE_URL', 'https://api.groq.com/openai/v1')}, model={MODEL_NAME}): {exc}") from exc

    raw_content = response.choices[0].message.content or ""

    # Defensive: strip ```json ... ``` fences in case the model adds them
    # despite being told not to.
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


def validate_and_filter(questions: List[AIQuestion]) -> List[AIQuestion]:
    """
    V1 validation pass:
    - exactly 4 options
    - correct_option index is in range
    - drop exact-duplicate question text (case-insensitive)
    V2 will add semantic-similarity duplicate detection and
    re-generation of rejected questions.
    """
    seen_texts = set()
    valid_questions: List[AIQuestion] = []

    for q in questions:
        normalized = q.question.strip().lower()

        if len(q.options) != 4:
            continue
        if not (0 <= q.correct_option < 4):
            continue
        if normalized in seen_texts:
            continue

        seen_texts.add(normalized)
        valid_questions.append(q)

    return valid_questions
