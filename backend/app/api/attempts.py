from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import (
    AttemptStartRequest,
    AttemptStartOut,
    AttemptSubmitRequest,
    AttemptResultOut,
    AnswerReview,
    AttemptHistoryItem,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/start", response_model=AttemptStartOut)
def start_attempt(
    request: AttemptStartRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == request.quiz_id).first()

    # Previously trusted a client-supplied user_id with no ownership check
    # on the quiz at all - anyone could start (and submit) an attempt on
    # someone else's quiz just by guessing its id.
    if not quiz or quiz.quiz_set.document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    attempt = models.Attempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        total_questions=len(quiz.questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return AttemptStartOut(attempt_id=attempt.id, quiz=quiz)


@router.post("/{attempt_id}/submit", response_model=AttemptResultOut)
def submit_attempt(
    attempt_id: int,
    request: AttemptSubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = db.query(models.Attempt).filter(models.Attempt.id == attempt_id).first()
    if not attempt or attempt.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if attempt.is_completed:
        raise HTTPException(status_code=400, detail="Attempt already submitted.")

    questions_by_id = {q.id: q for q in attempt.quiz.questions}
    score = 0
    review = []

    for submitted in request.answers:
        question = questions_by_id.get(submitted.question_id)
        if not question:
            continue

        is_correct = submitted.selected_option_index == question.correct_option_index
        if is_correct:
            score += 1

        db.add(
            models.Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_index=submitted.selected_option_index,
                is_correct=is_correct,
            )
        )

        review.append(
            AnswerReview(
                question_id=question.id,
                question_text=question.question_text,
                selected_option_index=submitted.selected_option_index,
                correct_option_index=question.correct_option_index,
                is_correct=is_correct,
                explanation=question.explanation,
            )
        )

    attempt.score = score
    attempt.total_questions = len(questions_by_id)
    attempt.is_completed = True
    attempt.completed_at = datetime.utcnow()
    db.commit()

    percentage = round((score / attempt.total_questions) * 100, 2) if attempt.total_questions else 0.0

    return AttemptResultOut(
        attempt_id=attempt.id,
        score=score,
        total_questions=attempt.total_questions,
        percentage=percentage,
        answers=review,
    )


@router.get("/mine", response_model=list[AttemptHistoryItem])
def get_my_history(
    document_id: Optional[int] = Query(
        None, description="Limit to attempts on one study material instead of all of them."
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Attempt).filter(models.Attempt.user_id == current_user.id)

    if document_id is not None:
        query = (
            query.join(models.Quiz, models.Attempt.quiz_id == models.Quiz.id)
            .join(models.QuizSet, models.Quiz.quiz_set_id == models.QuizSet.id)
            .filter(models.QuizSet.document_id == document_id)
        )

    return query.order_by(models.Attempt.started_at.desc()).all()


@router.get("/{attempt_id}", response_model=AttemptResultOut)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = db.query(models.Attempt).filter(models.Attempt.id == attempt_id).first()
    if not attempt or attempt.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if not attempt.is_completed:
        raise HTTPException(status_code=400, detail="Attempt not yet submitted.")

    questions_by_id = {q.id: q for q in attempt.quiz.questions}
    review = [
        AnswerReview(
            question_id=a.question_id,
            question_text=questions_by_id[a.question_id].question_text,
            selected_option_index=a.selected_option_index,
            correct_option_index=questions_by_id[a.question_id].correct_option_index,
            is_correct=a.is_correct,
            explanation=questions_by_id[a.question_id].explanation,
        )
        for a in attempt.answers
    ]

    percentage = round((attempt.score / attempt.total_questions) * 100, 2) if attempt.total_questions else 0.0

    return AttemptResultOut(
        attempt_id=attempt.id,
        score=attempt.score,
        total_questions=attempt.total_questions,
        percentage=percentage,
        answers=review,
    )
