from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import schemas, utils, responses
from .database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Todo lo que va antes del yield corre al ARRANCAR
    init_db()
    yield
    # Todo lo que va despues del yield corre al APAGAR (por ahora nada)

app = FastAPI(title="Futbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ajusta al puerto de tu React
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
    except schemas.ClubAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Club already in use.",
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

def auth_login(email: str, password: str, db: Session = None):
    # Logica real usando utils (si no esta mockeada por pytest)
    if db:
        user = utils.authenticate_user(db, email=email, password=password)
        if not user:
            return None
        return "abc123token" # Aqui luego generariamos un token real (ej. JWT)
    return None


@app.post("/auth/login/", tags=["Login"])
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    token = auth_login(credentials.email, credentials.password, db)
    
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "401 Unauthorized",
                "message": "Invalid email or password."
            }
        )
    
    return {
        "status": "200",
        "data": {
            "access_token": token,
            "token_type": "bearer"
        },
        "message": "Login successful."
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

