from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import QuizGenerateRequest, QuizOut
from app.services.pdf_service import chunk_text, select_relevant_chunks
from app.services.ai_service import generate_quiz_questions, AIServiceError

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

MAX_QUIZZES_PER_DOCUMENT = 3


@router.post("/generate", response_model=QuizOut)
def generate_quiz(request: QuizGenerateRequest, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.status != "processed" or not document.extracted_text:
        raise HTTPException(status_code=400, detail="Document text is not ready yet.")

    quiz_set = (
        db.query(models.QuizSet)
        .filter(models.QuizSet.document_id == document.id)
        .first()
    )
    if not quiz_set:
        quiz_set = models.QuizSet(document_id=document.id)
        db.add(quiz_set)
        db.commit()
        db.refresh(quiz_set)

    existing_quiz_count = (
        db.query(models.Quiz).filter(models.Quiz.quiz_set_id == quiz_set.id).count()
    )
    if existing_quiz_count >= MAX_QUIZZES_PER_DOCUMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_QUIZZES_PER_DOCUMENT} quizzes per material reached.",
        )

    chunks = chunk_text(document.extracted_text)
    relevant_chunks = select_relevant_chunks(chunks)

    try:
        ai_questions = generate_quiz_questions(relevant_chunks, request.num_questions)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not ai_questions:
        raise HTTPException(
            status_code=502,
            detail="AI returned no valid questions after validation (all failed the option/duplicate checks).",
        )

    quiz = models.Quiz(
        quiz_set_id=quiz_set.id,
        quiz_number=existing_quiz_count + 1,
        num_questions=len(ai_questions),
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    for ai_q in ai_questions:
        question = models.Question(
            quiz_id=quiz.id,
            question_text=ai_q.question,
            correct_option_index=ai_q.correct_option,
            explanation=ai_q.explanation,
            topic=ai_q.topic,
            difficulty=ai_q.difficulty,
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for idx, option_text in enumerate(ai_q.options):
            db.add(
                models.QuestionOption(
                    question_id=question.id,
                    option_index=idx,
                    option_text=option_text,
                )
            )
        db.commit()

    db.refresh(quiz)
    return quiz


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")
    return quiz


@router.get("/document/{document_id}", response_model=list[QuizOut])
def list_quizzes_for_document(document_id: int, db: Session = Depends(get_db)):
    quiz_set = (
        db.query(models.QuizSet).filter(models.QuizSet.document_id == document_id).first()
    )
    if not quiz_set:
        return []
    return db.query(models.Quiz).filter(models.Quiz.quiz_set_id == quiz_set.id).all()
