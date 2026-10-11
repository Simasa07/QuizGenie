# Test Suite — AI Live Quiz Engine Backend

## Summary

- **106 tests, 0 failures**, 92% overall code coverage
- Mix of **unit tests** (pure functions, no DB/network) and **integration
  tests** (real HTTP calls through FastAPI's `TestClient`, against a real,
  isolated in-memory SQLite database)
- All AI calls are **mocked** — no real Groq/Gemini API key or network
  access is needed to run this suite

## How to run it

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

With coverage (what generated `test_reports/`):

```bash
python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html:test_reports/htmlcov
```

Open `test_reports/htmlcov/index.html` in a browser for a line-by-line
coverage view.

## What's tested

| File | What it covers |
|---|---|
| `test_unit_security.py` | Password hashing (bcrypt) and JWT tokens — round-trip, tampering, wrong secret, expiry |
| `test_unit_pdf_service.py` | Text cleaning, chunking, chunk selection |
| `test_unit_ai_validation.py` | Question validation: option count, correct-answer range, exact + near-duplicate detection |
| `test_unit_ai_recommendation.py` | Study-tip generation: token ceiling sent to the model, word limit + weakest-topic wording in the prompt, trimming of a reply cut off mid-sentence, empty/failed AI replies |
| `test_integration_auth.py` | Signup, password is actually hashed in the DB (not plaintext), login success/failure, no user-enumeration via error messages, token required/validated on protected endpoints |
| `test_integration_documents.py` | PDF upload, duplicate-filename blocking (per-user), **cross-user isolation** |
| `test_integration_quizzes.py` | Quiz generation, question-count cap (1–30), 3-quizzes-per-document cap, independent time limit, **cross-user isolation** |
| `test_integration_attempts.py` | Scoring correctness, can't resubmit, **cross-user isolation** on starting/submitting/reading attempts |
| `test_integration_analytics.py` | Weak-topic threshold math, overview totals, document-scoped filtering, **cross-user isolation** |

The tests marked **cross-user isolation** are the most important ones from
a security standpoint — they prove that one logged-in user genuinely
cannot read or act on another user's documents, quizzes, attempts, or
analytics, which is the entire point of the auth system.

## Coverage gap (expected, not a bug)

`app/services/ai_service.py` sits at 74% coverage. The study-tip path is now
covered with a fake client; the remaining uncovered lines are the quiz-generation
network call — the real `client.chat.completions.create()` call to Groq/Gemini. Tests mock `generate_quiz_questions` and
`generate_study_recommendation` at the router level (see
`mock_ai_quiz_generation` and `mock_ai_recommendation` in `conftest.py`)
rather than making real API calls, so this suite can run anywhere, instantly,
without an API key or quota cost. The validation/filtering logic *around*
those calls (`validate_and_filter`, duplicate detection) is fully covered
separately in `test_unit_ai_validation.py`.

## Fixtures (see `conftest.py`)

- `client` — a `TestClient` wired to an isolated in-memory test database
  (never touches your real Postgres DB)
- `signup(email, password, username)` — creates a user, returns headers/id/token
- `upload_document(headers, filename)` — uploads a real tiny PDF built with PyMuPDF
- `mock_ai_quiz_generation` — replaces the real AI quiz call with deterministic fake questions
- `generate_quiz(headers, document_id, ...)` — generates a quiz using the mock above
- `mock_ai_recommendation` — replaces the real AI recommendation call
