from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import schemas, utils, product_repository as repo

from .database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Todo lo que va antes del yield corre al ARRANCAR
    init_db()
    yield
    # Todo lo que va después del yield corre al APAGAR (por ahora nada)

app = FastAPI(title="Futbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ajustá al puerto de tu React
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return utils.register_user(db, user_in)
    except schemas.UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already in use.",
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)