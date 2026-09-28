from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import product_repository as repo
from . import schemas
from .database import get_db, init_db

app = FastAPI(title="Futbot API")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/auth/register",
        response_model=schemas.UserOut,
        status_code=status.HTTP_201_CREATED,
        tags=["users"],
)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = repo.get_user_by_email_or_username(
        db, email=user_in.email, username=user_in.username
    )
    if existing:
        if existing.email == user_in.email:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        raise HTTPException(status_code=400, detail="El username ya está en uso")

    return repo.create_user(db, user_in)

