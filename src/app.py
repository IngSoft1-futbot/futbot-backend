from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from contextlib import asynccontextmanager

from . import schemas, utils, responses
from .database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    try: # Antes del yield: corre al ARRANCAR (crea tablas y siembra el behavior 0)
        init_db()
    except SQLAlchemyError:
        print("WARNING: database not available")
    yield
    # Despues del yield: corre al APAGAR (por ahora nada)
 
 
app = FastAPI(title="Futbot API", lifespan=lifespan)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ajustar al puerto del React
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )
    return {"status": "ok", "database": "online"}
 

# Configuracion de seguridad para extraer el token Bearer del header
security = HTTPBearer()

security_optional = HTTPBearer(auto_error=False)

#Funcion de seguridad para proteger rutas privadas.Extrae el token Bearer del header de la peticion, lo valida utilizando la capa de utilidades y retorna el ID del usuario si es legitimo
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Dependencia de FastAPI para proteger rutas. 
    Intercepta el token, lo valida usando utils y devuelve el id del usuario.
    """
    try:
        return utils.verify_jwt_token(credentials.credentials)
    except schemas.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )

@app.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,  
    tags=["Users"],
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

@app.post("/auth/login/", tags=["Users"], responses=responses.LOGIN_RESPONSES) 
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db),auth_header: HTTPAuthorizationCredentials | None = Depends(security_optional)):

    if auth_header:
        try: 
            utils.verify_jwt_token(auth_header.credentials)
            # Si pasa sin errores, significa que el token es VALIDO y ACTIVO ppor lo que el usuario ya tiene un token
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya posees un token activo. No puedes volver a iniciar sesion."
            )
        except schemas.InvalidTokenError:
            # Si mandan un token corrupto o inventado, cortamos con unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )


    # Delegamos la autenticacion y la generacion del token a la capa de utils
    token = utils.authenticate_and_create_token(db, email=credentials.email, password=credentials.password)
    
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


@app.post(
    "/users/{user_id}/teams",
    response_model=schemas.TeamOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Teams"],
    responses=responses.CREATE_TEAM_RESPONSES
)
def create_team (user_id: int, team_in: schemas.TeamCreate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user_id)):

    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create teams for another user.",
        )
    try:
        return utils.create_team(db, user_id, team_in)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User can not find."
        )
    except schemas.PlayerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player can not find."
        )
    except schemas.BehaviorNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Behavior can not find."
        )
    except schemas.PlayerNotAuthorizedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the owner of the player."
        )
    except schemas.BehaviorNotAuthorizedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the owner of the behavior."
        )
    except schemas.TeamNameAlreadyInUseError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Team name already in use for this user."
        )
    except schemas.TeamIncompleteError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Team incomplete, must be 3 starters & 3 subtitutes."
        )
    except schemas.PlayerAlreadyInUseError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Some players are already in use."
        )
    except schemas.CreateTeamError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict in creation time."
        )

@app.get(
    "/friendlymatches",
    response_model=list[schemas.FriendlyMatchOut],
    status_code=status.HTTP_200_OK,
    tags=["Matches"],
    responses=responses.GET_FRIENDLY_MATCHES_RESPONSES
)
def get_friendly_matches(db: Session = Depends(get_db)):
    try:
        return utils.get_available_friendly_matches(db)
    except schemas.FriendlyMatchesError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving teams."
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

