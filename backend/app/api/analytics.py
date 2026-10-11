from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import TopicStat, OverviewStats, AttemptHistoryItem, RecommendationOut
from app.services.ai_service import generate_study_recommendation, AIServiceError
from app.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

# A topic's accuracy below this is flagged "weak" for the student to focus on.
WEAK_TOPIC_THRESHOLD = 60.0


def _compute_topic_stats(db: Session, user_id: int, document_id: Optional[int]) -> list[TopicStat]:
    """
    Aggregates every answer the user has ever submitted, grouped by the
    question's topic, across all completed attempts. Weakest topics first.
    user_id here always comes from the authenticated caller, never from a
    client-supplied parameter.
    """
    query = (
        db.query(models.Answer, models.Question.topic)
        .join(models.Attempt, models.Answer.attempt_id == models.Attempt.id)
        .join(models.Question, models.Answer.question_id == models.Question.id)
        .join(models.Quiz, models.Question.quiz_id == models.Quiz.id)
        .join(models.QuizSet, models.Quiz.quiz_set_id == models.QuizSet.id)
        .filter(models.Attempt.user_id == user_id, models.Attempt.is_completed.is_(True))
    )
    if document_id is not None:
        query = query.filter(models.QuizSet.document_id == document_id)

    topic_totals: dict[str, dict[str, int]] = {}
    for answer, topic in query.all():
        key = topic or "General"
        bucket = topic_totals.setdefault(key, {"total": 0, "correct": 0})
        bucket["total"] += 1
        if answer.is_correct:
            bucket["correct"] += 1

    stats = []
    for topic, counts in topic_totals.items():
        accuracy = (counts["correct"] / counts["total"] * 100) if counts["total"] else 0.0
        stats.append(
            TopicStat(
                topic=topic,
                total_answered=counts["total"],
                correct=counts["correct"],
                accuracy_percentage=round(accuracy, 1),
                is_weak=accuracy < WEAK_TOPIC_THRESHOLD,
            )
        )

    stats.sort(key=lambda s: s.accuracy_percentage)
    return stats


@router.get("/mine/topics", response_model=list[TopicStat])
def get_my_topic_stats(
    document_id: Optional[int] = Query(
        None, description="Limit to one study material instead of all of them."
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _compute_topic_stats(db, current_user.id, document_id)


@router.get("/mine/overview", response_model=OverviewStats)
def get_my_overview(
    document_id: Optional[int] = Query(
        None, description="Limit to one study material instead of all of them."
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Attempt).filter(
        models.Attempt.user_id == current_user.id, models.Attempt.is_completed.is_(True)
    )

    if document_id is not None:
        query = (
            query.join(models.Quiz, models.Attempt.quiz_id == models.Quiz.id)
            .join(models.QuizSet, models.Quiz.quiz_set_id == models.QuizSet.id)
            .filter(models.QuizSet.document_id == document_id)
        )

    attempts = query.order_by(models.Attempt.completed_at.desc()).all()

    total_attempts = len(attempts)
    total_questions = sum(a.total_questions or 0 for a in attempts)
    total_correct = sum(a.score or 0 for a in attempts)
    overall_accuracy = (total_correct / total_questions * 100) if total_questions else 0.0

    recent = [AttemptHistoryItem.model_validate(a) for a in attempts[:10]]

    return OverviewStats(
        total_attempts=total_attempts,
        total_questions_answered=total_questions,
        total_correct=total_correct,
        overall_accuracy_percentage=round(overall_accuracy, 1),
        recent_attempts=recent,
    )


@router.get("/mine/recommendation", response_model=RecommendationOut)
def get_my_recommendation(
    document_id: Optional[int] = Query(
        None, description="Limit to one study material instead of all of them."
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stats = _compute_topic_stats(db, current_user.id, document_id)

    if not stats:
        return RecommendationOut(
            recommendation="Take a quiz on this material to get personalized study tips.",
            weak_topics=[],
        )

    weak_topics = [s.topic for s in stats if s.is_weak]

    try:
        text = generate_study_recommendation(stats)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return RecommendationOut(recommendation=text, weak_topics=weak_topics)
