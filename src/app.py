from fastapi.responses import JSONResponse
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from contextlib import asynccontextmanager
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

from . import schemas, utils, responses, product_repository
from .database import get_db, init_db
from .simulation import partidos_activos, Amistoso


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:  # Antes del yield: corre al ARRANCAR (crea tablas y siembra el behavior 0)
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


# Funcion de seguridad para proteger rutas privadas.Extrae el token Bearer del header de la peticion, lo valida utilizando la capa de utilidades y retorna el ID del usuario si es legitimo
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Dependencia de FastAPI para proteger rutas.
    Intercepta el token, lo valida usando utils y devuelve el id del usuario.
    """
    try:
        return utils.verify_jwt_token(credentials.credentials)
    except schemas.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )


@app.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    responses=responses.REGISTER_RESPONSES,
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
            detail=str(e),
        )
    except schemas.RegistrationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict in register time.",
        )


@app.post("/auth/login", tags=["Users"], responses=responses.LOGIN_RESPONSES)
def login(
    credentials: schemas.LoginRequest,
    db: Session = Depends(get_db),
    auth_header: HTTPAuthorizationCredentials | None = Depends(security_optional),
):

    if auth_header:
        try:
            utils.verify_jwt_token(auth_header.credentials)
            # Si pasa sin errores, significa que el token es VALIDO y ACTIVO ppor lo que el usuario ya tiene un token
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya posees un token activo. No puedes volver a iniciar sesion.",
            )
        except schemas.InvalidTokenError:
            # Si mandan un token corrupto o inventado, cortamos con unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
            )

    # Delegamos la autenticacion y la generacion del token a la capa de utils
    token = utils.authenticate_and_create_token(
        db, email=credentials.email, password=credentials.password
    )

    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "401 Unauthorized",
                "message": "Invalid email or password.",
            },
        )

    return {
        "status": "200",
        "data": {"access_token": token, "token_type": "bearer"},
        "message": "Login successful.",
    }


@app.get(
    "/users/{user_id}/players",
    response_model=list[schemas.PlayerOut],
    tags=["Players"],
    responses=responses.GET_PLAYERS_RESPONSES,
)
def get_players(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):

    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view players of another user.",
        )
    try:
        return utils.get_players(db, user_id)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User could not be found."
        )


@app.get(
    "/users/{user_id}/behaviors",
    response_model=schemas.BehaviorsListResponse,
    tags=["Behaviors"],
)
def get_behaviors(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view behaviors of another user.",
        )
    try:
        behaviors = utils.get_behaviors(db, user_id)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User could not be found.",
        )
    return schemas.BehaviorsListResponse(
        status="200",
        data=[
            schemas.BehaviorSummaryOut(
                behavior_id=behavior.id_behavior,
                name=behavior.name,
            )
            for behavior in behaviors
        ],
        message="Behaviors listed successfully.",
    )


@app.post(
    "/users/{user_id}/players",
    response_model=schemas.PlayerOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Players"],
    responses=responses.CREATE_PLAYER_RESPONSES,
)
def create_player(
    user_id: int,
    player_in: schemas.PlayerIn,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):

    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create players for another user.",
        )
    try:
        return utils.create_player(db, user_id, player_in)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User could not be found."
        )
    except schemas.PointAssignmentError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Points must total 300, each between 20 and 100.",
        )


@app.post(
    "/users/{user_id}/teams",
    response_model=schemas.TeamOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Teams"],
    responses=responses.CREATE_TEAM_RESPONSES,
)
def create_team(
    user_id: int,
    team_in: schemas.TeamCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):

    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create teams for another user.",
        )
    try:
        return utils.create_team(db, user_id, team_in)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User can not find."
        )
    except schemas.PlayerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player can not find."
        )
    except schemas.BehaviorNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Behavior can not find."
        )
    except schemas.PlayerNotAuthorizedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the owner of the player.",
        )
    except schemas.BehaviorNotAuthorizedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not the owner of the behavior.",
        )
    except schemas.TeamNameAlreadyInUseError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already in use for this user.",
        )
    except schemas.TeamIncompleteError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team incomplete, must be 3 starters & 3 subtitutes.",
        )
    except schemas.PlayerAlreadyInUseError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some players are already in use.",
        )
    except schemas.CreateTeamError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conflict in creation time."
        )


@app.get(
    "/users/{user_id}/teams",
    response_model=schemas.TeamsListResponse,
    tags=["Teams"],
)
def get_teams(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view teams of another user.",
        )
    try:
        teams = utils.get_teams(db, user_id)
    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User could not be found.",
        )
    return schemas.TeamsListResponse(
        status="200",
        data=[
            schemas.TeamSummaryOut(
                team_id=team.team_id,
                name=team.name,
            )
            for team in teams
        ],
        message="Teams listed successfully.",
    )


@app.get(
    "/friendly-matches",
    response_model=list[schemas.GETFriendlyMatchOut],
    status_code=status.HTTP_200_OK,
    tags=["Friendly Matches"],
    responses=responses.GET_FRIENDLY_MATCHES_RESPONSES,
)
def get_friendly_matches(db: Session = Depends(get_db)):
    try:
        return utils.get_available_friendly_matches(db)
    except schemas.FriendlyMatchesError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving matches.",
        )


@app.get(
    "/friendly-matches/{match_id}",
    response_model=schemas.FriendlyMatchOut,
    tags=["Friendly Matches"],
)
def get_friendly_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return utils.get_friendly_match_for_user(db, current_user_id, match_id)
    except schemas.MatchNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found.")
    except schemas.MatchNotAuthorizedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "User is not authorized to view this match.",
        )


@app.post(
    "/users/{user_id}/friendly-matches",
    response_model=schemas.FriendlyMatchOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Friendly Matches"],
    responses=responses.CREATE_FRIENDLY_MATCH_RESPONSES,
)
def create_friendly_match(
    user_id: int,
    match_in: schemas.FriendlyMatchCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # 1. Seguridad: Verificar que el usuario del token sea el mismo que intenta crear el partido
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create matches for another user.",
        )

    # 2. Llamar a la logica de negocio y manejar excepciones (ya sin validar user_id en el body)
    try:
        return utils.create_friendly_match(db, user_id, match_in)

    except schemas.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    except schemas.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or does not belong to the user.",
        )
    except schemas.InvalidDurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except schemas.TeamIncompleteError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team incomplete, must have exactly 3 starters.",
        )
    except schemas.CreateMatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conflict in match creation."
        )


@app.post(
    "/friendly-matches/{match_id}/join",
    response_model=schemas.FriendlyMatchOut,
    tags=["Friendly Matches"],
    responses=responses.JOIN_FRIENDLY_MATCH_RESPONSES,
)
@app.put(
    "/friendly-matches/{match_id}/away-team",
    response_model=schemas.FriendlyMatchOut,
    tags=["Friendly Matches"],
    responses=responses.JOIN_FRIENDLY_MATCH_RESPONSES,
)
def join_friendly_match(
    match_id: int,
    join_in: schemas.JoinMatch,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):

    try:
        return utils.join_friendly_match(db, current_user_id, match_id, join_in)
    except schemas.MatchNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found.")
    except schemas.TeamNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found.")
    except schemas.TeamNotAuthorizedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "User is not the owner of the team."
        )
    except schemas.MatchNotAuthorizedError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "User is not authorized to join this match."
        )
    except schemas.JoinOwnMatchError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "User cannot join their own match."
        )
    except schemas.TeamIncompleteError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Team incomplete, must have exactly 3 starters.",
        )
    except schemas.MatchAlreadyTakenError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Unable to join: another player has already joined.",
        )
    except schemas.MatchNotJoinableError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The match is no longer available: it is in progress, finished, or cancelled.",
        )

@app.websocket("/ws/amistoso/{match_id}")
async def ws_amistoso(
    websocket: WebSocket,
    match_id: int,
    token: str,                       # llega como ?token=... en la URL
):
    # 1. Autenticación: el user_id sale del token
    try:
        user_id = utils.verify_jwt_token(token)
    except schemas.InvalidTokenError:
        await websocket.close(code=1008)   # policy violation
        return

    await websocket.accept()

    # 2. Si el partido no existe, lo instanciamos inyectando el cargador seguro para hilos
    if match_id not in partidos_activos:
        partidos_activos[match_id] = Amistoso(
            match_id,
            cargar_alineacion=lambda uid: product_repository.cargar_alineacion_por_equipo(match_id, uid)
        )
    
    partido = partidos_activos[match_id]

    # 3. Unimos al jugador y guardamos su rol (jugador o espectador)
    rol = await partido.unir_jugador(user_id, websocket)

    # Por seguridad, si el socket se desconectó por algún motivo, cortamos acá
    from starlette.websockets import WebSocketState
    if websocket.client_state == WebSocketState.DISCONNECTED:
        return

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:  # JSON inválido
                await websocket.send_json({"tipo": "error", "mensaje": "JSON inválido."})
                continue

            # 4. Chequeamos el ROL: Solo los jugadores activos pueden mandar comandos
            if rol == "jugador":
                ok, msg = partido.aplicar_accion(user_id, data)
                if not ok:
                    await websocket.send_json({"tipo": "error", "mensaje": msg})
            else:
                await websocket.send_json({"tipo": "error", "mensaje": "Los espectadores no pueden enviar comandos."})

    except WebSocketDisconnect:
        print(f"El usuario {user_id} cerró la conexión del partido {match_id}.")
        await partido.desconectar(user_id, websocket)

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
