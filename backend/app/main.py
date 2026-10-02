from fastapi import FastAPI

from app.database.database import Base, engine
from app.database import models  # noqa: F401 (needed so models register with Base)
from app.api import users, documents, quizzes, attempts

# V1: create tables directly from models. Move to Alembic migrations
# once the schema starts changing between V1 and V2.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Live Quiz Engine", version="0.1.0")

app.include_router(users.router)
app.include_router(documents.router)
app.include_router(quizzes.router)
app.include_router(attempts.router)


@app.get("/")
def root():
    return {"message": "AI Live Quiz Engine API is running."}


@app.get("/health")
def health_check():
    return {"status": "ok"}
