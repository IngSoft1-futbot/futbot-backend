from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import schemas, utils, product_repository as repo, responses
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
    responses=responses.REGISTER_RESPONSES
)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return utils.register_user(db, user_in)
    except schemas.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use.",
        )
    except schemas.UsernameAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already in use.",
        )
    except schemas.PasswordValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= str(e),
        )
    except schemas.RegistrationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict in register time.",
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)