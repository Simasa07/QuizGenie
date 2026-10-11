import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import DocumentOut
from app.services.pdf_service import extract_text_from_pdf, clean_text
from app.api.deps import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported in V1.")

    existing = (
        db.query(models.Document)
        .filter(models.Document.user_id == current_user.id, models.Document.filename == file.filename)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"You already uploaded a file named '{file.filename}'. Rename it or delete the existing one first.",
        )

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = models.Document(
        user_id=current_user.id,
        filename=file.filename,
        filepath=filepath,
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        raw_text = extract_text_from_pdf(filepath)
        document.extracted_text = clean_text(raw_text)
        document.status = "processed"
    except Exception:
        document.status = "failed"

    db.commit()
    db.refresh(document)

    return document


@router.get("/mine", response_model=list[DocumentOut])
def list_my_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Document).filter(models.Document.user_id == current_user.id).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()

    # Same 404 whether the document doesn't exist at all, or it exists but
    # belongs to someone else - this previously had NO ownership check at
    # all, so any logged-in user could read any other user's document by
    # guessing/incrementing the id.
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found.")

    return document
