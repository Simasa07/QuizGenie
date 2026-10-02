from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/start", response_model=AttemptStartOut)
def start_attempt(request: AttemptStartRequest, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == request.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    attempt = models.Attempt(
        quiz_id=quiz.id,
        user_id=user.id,
        total_questions=len(quiz.questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return AttemptStartOut(attempt_id=attempt.id, quiz=quiz)


@router.post("/{attempt_id}/submit", response_model=AttemptResultOut)
def submit_attempt(attempt_id: int, request: AttemptSubmitRequest, db: Session = Depends(get_db)):
    attempt = db.query(models.Attempt).filter(models.Attempt.id == attempt_id).first()
    if not attempt:
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


@router.get("/{attempt_id}", response_model=AttemptResultOut)
def get_attempt(attempt_id: int, db: Session = Depends(get_db)):
    attempt = db.query(models.Attempt).filter(models.Attempt.id == attempt_id).first()
    if not attempt:
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


@router.get("/user/{user_id}", response_model=list[AttemptHistoryItem])
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Attempt)
        .filter(models.Attempt.user_id == user_id)
        .order_by(models.Attempt.started_at.desc())
        .all()
    )
