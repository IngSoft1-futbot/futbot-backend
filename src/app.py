from fastapi.responses import JSONResponse
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import schemas, utils, responses
from .database import get_db, init_db
from .product_repository import auth_login , create_player
from .utils import verify_player

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
    
@app.post("/users/{user_id}/players")
def create_user_player(user_id : int, player : schemas.PlayerIn):


    if (not verify_player(player)):
       return JSONResponse(
            status_code=400,
            content={
                "status": "400 Bad Request",
                "message": "PACSS attributes exceed the maximum allowed points."
            })
       
    
    created_player : schemas.PlayerOut = create_player(user_id ,player)
        
    content = {
             "status": "201",
             "data": created_player.model_dump(),
                "message": "Player created successfully"
         }
    return JSONResponse(status_code = 201,
    content=content)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
