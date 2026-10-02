import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import DocumentOut
from app.services.pdf_service import extract_text_from_pdf, clean_text

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentOut)
def upload_document(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported in V1.")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = models.Document(
        user_id=user_id,
        filename=file.filename,
        filepath=filepath,
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Extract text right away so quiz generation can use it later.
    try:
        raw_text = extract_text_from_pdf(filepath)
        document.extracted_text = clean_text(raw_text)
        document.status = "processed"
    except Exception:
        document.status = "failed"

    db.commit()
    db.refresh(document)

    return document


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/user/{user_id}", response_model=list[DocumentOut])
def list_user_documents(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Document).filter(models.Document.user_id == user_id).all()

