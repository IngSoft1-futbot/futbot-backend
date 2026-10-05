from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import pytest
import jwt
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src import schemas, utils

USER_IN = schemas.UserCreate(
    club="juan",
    name="Juan",
    email="Juan@Gmail.com",
    password="Clave123!",
)


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def repo_mock():
    with patch("src.utils.repo") as mock:
        yield mock


# ---------- password_validation (función pura, sin mocks) ----------

@pytest.mark.parametrize("pwd, mensaje", [
    ("Cl1!", "between"),                  # muy corta
    ("Clave123!" + "a" * 40, "between"),  # muy larga
    ("Clavesola!", "digit"),              # sin número
    ("clave123!", "uppercase"),           # sin mayúscula
    ("CLAVE123!", "lowercase"),           # sin minúscula
    ("Clave1234", "special"),             # sin símbolo
])
def test_password_invalida(pwd, mensaje):
    with pytest.raises(schemas.PasswordValidationError) as exc:
        utils.password_validation(pwd)

    assert mensaje in str(exc.value)


def test_password_valida():
    utils.password_validation("Clave123!")   # no debe lanzar nada


# ---------- register_user ----------

def test_register_password_invalida_no_toca_la_base(repo_mock):
    bad = USER_IN.model_copy(update={"password": "abc"})

    with pytest.raises(schemas.PasswordValidationError):
        utils.register_user(MagicMock(), bad)

    repo_mock.get_user_by_email.assert_not_called()
    repo_mock.create_user.assert_not_called()


def test_register_email_ya_existe(repo_mock):
    repo_mock.get_user_by_email.return_value = object()

    with pytest.raises(schemas.EmailAlreadyExistsError):
        utils.register_user(MagicMock(), USER_IN)

    repo_mock.get_user_by_club.assert_not_called()
    repo_mock.create_user.assert_not_called()


def test_register_club_ya_existe(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = object()

    with pytest.raises(schemas.ClubAlreadyExistsError):
        utils.register_user(MagicMock(), USER_IN)

    repo_mock.create_user.assert_not_called()


def test_register_ok(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = None

    utils.register_user(MagicMock(), USER_IN)

    repo_mock.create_user.assert_called_once()
    kwargs = repo_mock.create_user.call_args.kwargs
    assert kwargs["email"] == "juan@gmail.com"          # en minusculas
    assert kwargs["password_hash"] != "Clave123!"       # nunca en claro
    assert "password" not in kwargs


def test_register_integrity_error_se_convierte_en_registration_error(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = None
    repo_mock.create_user.side_effect = IntegrityError("stmt", {}, Exception())

    with pytest.raises(schemas.RegistrationError):
        utils.register_user(MagicMock(), USER_IN)

# --------------   TESTS DE LOGIN   --------------

def test_authenticate_user_exitoso():
    # 1. Creamos un usuario "falso" que devolveria la base de datos
    mock_user = MagicMock()
    mock_user.email = "juan@gmail.com"
    # Hasheamos una contraseña de prueba para que bcrypt.checkpw de True
    mock_user.password_hash = utils.hash_password("Pass1234!")

    # 2. Mockeamos el repositorio para que devuelva nuestro usuario falso cuando busquen por mail
    with patch("src.utils.repo.get_user_by_email", return_value=mock_user) as mock_get:
        db_session = MagicMock() # Mock de la sesion de base de datos
        
        # Ejecutamos la funcion de autenticacion con contraseña correcta
        user = utils.authenticate_user(db_session, email="juan@gmail.com", password="Pass1234!")

        # Verificaciones
        assert user is not None
        assert user.email == "juan@gmail.com"
        mock_get.assert_called_once_with(db_session, email="juan@gmail.com")


def test_authenticate_user_password_incorrecta():
    mock_user = MagicMock()
    mock_user.email = "juan@gmail.com"
    mock_user.password_hash = utils.hash_password("Pass1234!")

    with patch("src.utils.repo.get_user_by_email", return_value=mock_user):
        db_session = MagicMock()
        
        # Ejecutamos con contraseña INCORRECTA
        user = utils.authenticate_user(db_session, email="juan@gmail.com", password="ClaveFalsa1!")

        # Deberia fallar la verificacion de bcrypt 
        assert user is None


def test_authenticate_user_email_no_registrado():
    # Mockeamos el repositorio para que devuelva None (usuario no encontrado)
    with patch("src.utils.repo.get_user_by_email", return_value=None) as mock_get:
        db_session = MagicMock()
        
        user = utils.authenticate_user(db_session, email="noexiste@gmail.com", password="Pass1234!")

        assert user is None
        mock_get.assert_called_once_with(db_session, email="noexiste@gmail.com")

def test_authenticate_and_create_token_exitoso(repo_mock):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.password_hash = utils.hash_password("Pass1234!")

    with patch("src.utils.authenticate_user", return_value=mock_user):
        db_session = MagicMock()
        token = utils.authenticate_and_create_token(db_session, email="juan@gmail.com", password="Pass1234!")
        
        # Decodificamos el token generado para verificar que el payload sea correcto
        payload = jwt.decode(token, options={"verify_signature": False}) 
        assert payload["sub"] == str(mock_user.id)


def test_authenticate_and_create_token_falla(repo_mock):
    with patch("src.utils.authenticate_user", return_value=None):
        db_session = MagicMock()
        token = utils.authenticate_and_create_token(db_session, email="juan@gmail.com", password="MalPassword1!")
        
        assert token is None

#-------------------------------------Crear Equipo-----------------------------------------------
 
def make_player(pid, owner_id=1, team_id=None, shirt_number=10, behavior_id=0,
                is_starter=None, power=60, agility=60, control=60, speed=60, strength=60):
    return SimpleNamespace(
        player_id=pid,
        owner_id=owner_id,
        team_id=team_id,
        name=f"Jugador {pid}",
        shirt_number=shirt_number,
        behavior_id=behavior_id,
        is_starter=is_starter,
        power=power,
        agility=agility,
        control=control,
        speed=speed,
        strength=strength,
    )
 
 
def make_behavior(bid, creator_id=None, is_default=False):
    return SimpleNamespace(id_behavior=bid, creator_id=creator_id, is_default=is_default)
 
 
def make_team_in(titulares=(7, 8, 9), suplentes=(10, 11, 12), name="Mi Equipo"):
    return schemas.TeamCreate(
        name=name,
        jugadores_titulares=[{"player_id": i} for i in titulares],
        jugadores_suplentes=[{"player_id": i} for i in suplentes],
    )
 
 
# ============================== check_composition_and_duplicated
 
 
def test_composicion_ok():
    utils.check_composition_and_duplicated(make_team_in())  # no lanza
 
 
@pytest.mark.parametrize(
    "titulares, suplentes",
    [
        ((7, 8), (10, 11, 12)),
        ((7, 8, 9), (10, 11)),
        ((7, 8, 9), ()),
        ((7, 8, 9, 13), (10, 11)),  # suma 6 pero no es 3 + 3
        ((), ()),
    ],
)
def test_composicion_incompleta(titulares, suplentes):
    with pytest.raises(schemas.TeamIncompleteError):
        utils.check_composition_and_duplicated(make_team_in(titulares, suplentes))
 
 
def test_composicion_jugador_repetido_entre_titulares():
    with pytest.raises(schemas.PlayerAlreadyInUseError):
        utils.check_composition_and_duplicated(make_team_in((7, 7, 9), (10, 11, 12)))
 
 
def test_composicion_jugador_repetido_entre_titular_y_suplente():
    with pytest.raises(schemas.PlayerAlreadyInUseError):
        utils.check_composition_and_duplicated(make_team_in((7, 8, 9), (9, 11, 12)))
 
 
# ======================================================= check_players
 
 
def test_check_players_ok(db, repo_mock):
    repo_mock.get_players_by_ids.return_value = [make_player(7), make_player(8)]
 
    utils.check_players(db, 1, [7, 8])  # no lanza
 
 
def test_check_players_hace_una_sola_consulta(db, repo_mock):
    repo_mock.get_players_by_ids.return_value = [make_player(7), make_player(8)]
 
    utils.check_players(db, 1, [7, 8])
 
    repo_mock.get_players_by_ids.assert_called_once_with(db, ids=[7, 8])
 
 
def test_check_players_no_existe(db, repo_mock):
    repo_mock.get_players_by_ids.return_value = [make_player(7)]  # falta el 8
 
    with pytest.raises(schemas.PlayerNotFoundError):
        utils.check_players(db, 1, [7, 8])
 
 
def test_check_players_de_otro_usuario(db, repo_mock):
    repo_mock.get_players_by_ids.return_value = [make_player(7), make_player(8, owner_id=2)]
 
    with pytest.raises(schemas.PlayerNotAuthorizedError):
        utils.check_players(db, 1, [7, 8])
 
 
def test_check_players_ya_tiene_equipo(db, repo_mock):
    repo_mock.get_players_by_ids.return_value = [make_player(7), make_player(8, team_id=5)]
 
    with pytest.raises(schemas.PlayerAlreadyInUseError):
        utils.check_players(db, 1, [7, 8])
 
 
def test_check_players_ajeno_tiene_prioridad_sobre_en_uso(db, repo_mock):
    # De otro usuario Y con equipo: se informa 403, no 400 (no filtra datos ajenos)
    repo_mock.get_players_by_ids.return_value = [make_player(7, owner_id=2, team_id=5)]
 
    with pytest.raises(schemas.PlayerNotAuthorizedError):
        utils.check_players(db, 1, [7])
 
 
# ===================================================== check_behaviors
 
 
def test_check_behaviors_ok_propio_y_default(db, repo_mock):
    repo_mock.get_behaviors_by_ids.return_value = [
        make_behavior(0, is_default=True),
        make_behavior(5, creator_id=1),
    ]
 
    utils.check_behaviors(db, 1, {0, 5})  # no lanza
 
 
def test_check_behaviors_no_existe(db, repo_mock):
    repo_mock.get_behaviors_by_ids.return_value = [make_behavior(0, is_default=True)]
 
    with pytest.raises(schemas.BehaviorNotFoundError):
        utils.check_behaviors(db, 1, {0, 99})
 
 
def test_check_behaviors_de_otro_usuario(db, repo_mock):
    repo_mock.get_behaviors_by_ids.return_value = [make_behavior(5, creator_id=2)]
 
    with pytest.raises(schemas.BehaviorNotAuthorizedError):
        utils.check_behaviors(db, 1, {5})
 
 
def test_check_behaviors_default_es_de_todos(db, repo_mock):
    # creator_id=None y is_default=True: cualquier usuario lo puede usar
    repo_mock.get_behaviors_by_ids.return_value = [make_behavior(0, creator_id=None, is_default=True)]
 
    utils.check_behaviors(db, 999, {0})
 
 
# ================================================ resolve_behavior_id
 
 
def test_resolve_behavior_id_sin_eleccion_usa_default():
    assert utils.resolve_behavior_id(schemas.PlayerAssignment(player_id=7)) == utils.DEFAULT_BEHAVIOR_ID
    assert utils.DEFAULT_BEHAVIOR_ID == 0
 
 
def test_resolve_behavior_id_respeta_el_elegido():
    assert utils.resolve_behavior_id(schemas.PlayerAssignment(player_id=7, behavior_id=5)) == 5
 
 
def test_resolve_behavior_id_cero_explicito_se_mantiene():
    assert utils.resolve_behavior_id(schemas.PlayerAssignment(player_id=7, behavior_id=0)) == 0
 
 
# ======================================================= build_team_out
 
 
def test_build_team_out_separa_titulares_y_suplentes():
    team = SimpleNamespace(
        team_id=1,
        name="Mi Equipo",
        players=[
            make_player(7, is_starter=True),
            make_player(10, is_starter=False),
            make_player(8, is_starter=True),
            make_player(11, is_starter=False),
        ],
    )
 
    out = utils.build_team_out(team)
 
    assert isinstance(out, schemas.TeamOut)
    assert out.team_id == 1
    assert out.name == "Mi Equipo"
    assert [p.player_id for p in out.jugadores_titulares] == [7, 8]
    assert [p.player_id for p in out.jugadores_suplentes] == [10, 11]
 
 
def test_build_team_out_ordena_por_player_id():
    team = SimpleNamespace(
        team_id=1,
        name="Mi Equipo",
        players=[
            make_player(9, is_starter=True),
            make_player(7, is_starter=True),
            make_player(8, is_starter=True),
        ],
    )
 
    out = utils.build_team_out(team)
 
    assert [p.player_id for p in out.jugadores_titulares] == [7, 8, 9]
 
 
def test_build_team_out_incluye_nombre_y_behavior():
    team = SimpleNamespace(
        team_id=1,
        name="Mi Equipo",
        players=[make_player(7, behavior_id=5, is_starter=True)],
    )
 
    out = utils.build_team_out(team)
 
    assert out.jugadores_titulares[0].name == "Jugador 7"
    assert out.jugadores_titulares[0].behavior_id == 5
 
 
def test_build_team_out_sin_jugadores():
    out = utils.build_team_out(SimpleNamespace(team_id=1, name="Vacio", players=[]))
 
    assert out.jugadores_titulares == []
    assert out.jugadores_suplentes == []
 
 
# ========================================================== create_team
 
 
@pytest.fixture
def repo_team(repo_mock):
    """Repository configurado para el camino feliz de create_team."""
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_players_by_ids.return_value = [make_player(i) for i in range(7, 13)]
    repo_mock.get_behaviors_by_ids.return_value = [make_behavior(0, is_default=True)]
    repo_mock.get_team_by_owner_and_name.return_value = None
    repo_mock.add_team.return_value = SimpleNamespace(
        team_id=1,
        name="Mi Equipo",
        players=[make_player(i, team_id=1, is_starter=(i <= 9)) for i in range(7, 13)],
    )
    return repo_mock
 
 
def test_create_team_ok(db, repo_team):
    result = utils.create_team(db, 1, make_team_in())
 
    assert isinstance(result, schemas.TeamOut)
    assert result.team_id == 1
    assert [p.player_id for p in result.jugadores_titulares] == [7, 8, 9]
    assert [p.player_id for p in result.jugadores_suplentes] == [10, 11, 12]
 
 
def test_create_team_pasa_los_datos_correctos_al_repository(db, repo_team):
    utils.create_team(db, 1, make_team_in())
 
    kwargs = repo_team.add_team.call_args.kwargs
    assert kwargs["owner_id"] == 1
    assert kwargs["name"] == "Mi Equipo"
    # sin behavior elegido -> default (0)
    assert kwargs["starters"] == [(7, 0), (8, 0), (9, 0)]
    assert kwargs["substitutes"] == [(10, 0), (11, 0), (12, 0)]
 
 
def test_create_team_respeta_behavior_elegido(db, repo_team):
    repo_team.get_behaviors_by_ids.return_value = [
        make_behavior(0, is_default=True),
        make_behavior(5, creator_id=1),
    ]
    team_in = schemas.TeamCreate(
        name="Mi Equipo",
        jugadores_titulares=[
            {"player_id": 7, "behavior_id": 5},
            {"player_id": 8},
            {"player_id": 9},
        ],
        jugadores_suplentes=[{"player_id": i} for i in (10, 11, 12)],
    )
 
    utils.create_team(db, 1, team_in)
 
    assert repo_team.add_team.call_args.kwargs["starters"] == [(7, 5), (8, 0), (9, 0)]
 
 
def test_create_team_incompleto_falla_antes_de_consultar_la_base(db, repo_team):
    with pytest.raises(schemas.TeamIncompleteError):
        utils.create_team(db, 1, make_team_in((7, 8), (10, 11, 12)))
 
    repo_team.get_user.assert_not_called()
    repo_team.add_team.assert_not_called()
 
 
def test_create_team_usuario_inexistente(db, repo_team):
    repo_team.get_user.return_value = None
 
    with pytest.raises(schemas.UserNotFoundError):
        utils.create_team(db, 1, make_team_in())
 
    repo_team.add_team.assert_not_called()
 
 
def test_create_team_jugador_de_otro_usuario(db, repo_team):
    players = [make_player(i) for i in range(7, 12)] + [make_player(12, owner_id=2)]
    repo_team.get_players_by_ids.return_value = players
 
    with pytest.raises(schemas.PlayerNotAuthorizedError):
        utils.create_team(db, 1, make_team_in())
 
    repo_team.add_team.assert_not_called()
 
 
def test_create_team_behavior_de_otro_usuario(db, repo_team):
    repo_team.get_behaviors_by_ids.return_value = [make_behavior(0, creator_id=2, is_default=False)]
 
    with pytest.raises(schemas.BehaviorNotAuthorizedError):
        utils.create_team(db, 1, make_team_in())
 
    repo_team.add_team.assert_not_called()
 
 
def test_create_team_nombre_repetido_para_el_usuario(db, repo_team):
    repo_team.get_team_by_owner_and_name.return_value = SimpleNamespace(team_id=9)
 
    with pytest.raises(schemas.TeamNameAlreadyInUseError):
        utils.create_team(db, 1, make_team_in())
 
    repo_team.add_team.assert_not_called()
 
 
def test_create_team_integrity_error_se_traduce(db, repo_team):
    # Condicion de carrera: otro request creo el equipo entre el chequeo y el commit
    repo_team.add_team.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))
 
    with pytest.raises(schemas.CreateTeamError):
        utils.create_team(db, 1, make_team_in())

# --------------   TESTS DE AMISTOSOS   --------------

def test_get_friendly_matches_devuelve_lo_que_trae_el_repository(db, repo_mock):
    matches = [SimpleNamespace(id_match=1), SimpleNamespace(id_match=2)]
    repo_mock.get_open_friendly_matches.return_value = matches

    assert utils.get_available_friendly_matches(db) == matches
    repo_mock.get_open_friendly_matches.assert_called_once_with(db)


def test_get_friendly_matches_sin_partidos_devuelve_lista_vacia(db, repo_mock):
    repo_mock.get_open_friendly_matches.return_value = []

    assert utils.get_available_friendly_matches(db) == []


def test_get_friendly_matches_error_de_base_se_convierte_en_friendly_matches_error(db, repo_mock):
    repo_mock.get_open_friendly_matches.side_effect = SQLAlchemyError()

    with pytest.raises(schemas.FriendlyMatchesError):
        utils.get_available_friendly_matches(db)


def test_get_friendly_matches_no_esconde_errores_que_no_son_de_la_base(db, repo_mock):
    repo_mock.get_open_friendly_matches.side_effect = AttributeError()

    with pytest.raises(AttributeError):
        utils.get_available_friendly_matches(db)
 
 
# ---------- PlayerOut ----------
 
def test_player_out_se_construye_desde_un_objeto_orm():
    orm_player = SimpleNamespace(
        player_id=7, name="Lionel Messi", shirt_number=10, behavior_id=0,
        team_id=None, owner_id=1,                      # owner_id sobra: se ignora
        power=90, agility=95, control=60, speed=30, strength=25,
    )

    out = utils.build_player_out(orm_player)

    assert out.model_dump() == {
        "player_id": 7,
        "name": "Lionel Messi",
        "shirt_number": 10,
        "behavior_id": 0,
        "team_id": None,
        "pacss_attributes": {
            "power": 90, "agility": 95, "control": 60, "speed": 30, "strength": 25,
        },
    }
    
# ============================== Crear Jugador

def make_player_in(power=60, agility=60, control=60, speed=60, strength=60,
                   shirt_number=10, name="Jugador 7"):
    return schemas.PlayerIn(
        name=name,
        shirt_number=shirt_number,
        pacss_attributes=schemas.PacssAttributes(
            power=power, agility=agility, control=control,
            speed=speed, strength=strength,
        ),
    )


# ---------- validate_pacss / verify_player ----------

def test_validate_pacss_ok():
    assert utils.validate_pacss(make_player_in().pacss_attributes) is True


@pytest.mark.parametrize(
    "attrs",
    [
        dict(power=61),                           # suma 301
        dict(power=59),                           # suma 299
        dict(power=19, agility=61),               # suma 300 pero 19 < 20
        dict(power=101, agility=19, control=20,
             speed=80, strength=80),              # suma 300 pero 101 > 100
    ],
)
def test_validate_pacss_invalido(attrs):
    assert utils.validate_pacss(make_player_in(**attrs).pacss_attributes) is False


def test_validate_pacss_limites_validos():
    # 100 + 100 + 20 + 40 + 40 = 300, todos dentro de [20, 100]
    p = make_player_in(power=100, agility=100, control=20, speed=40, strength=40)
    assert utils.validate_pacss(p.pacss_attributes) is True


def test_verify_player_cambio_de_pacss():
    assert utils.verify_player(make_player_in()) is True
    assert utils.verify_player(make_player_in(power=100)) is False


# ---------- build_player_out ----------

def test_build_player_out_desde_objeto_orm():
    orm_player = SimpleNamespace(
        player_id=7, name="Lionel Messi", shirt_number=10, behavior_id=0,
        team_id=None, owner_id=1,                  # owner_id sobra: se ignora
        power=90, agility=95, control=60, speed=30, strength=25,
    )

    out = utils.build_player_out(orm_player)

    assert out.model_dump() == {
        "player_id": 7,
        "name": "Lionel Messi",
        "shirt_number": 10,
        "behavior_id": 0,
        "team_id": None,
        "pacss_attributes": {
            "power": 90, "agility": 95, "control": 60, "speed": 30, "strength": 25,
        },
    }


# ---------- create_player ----------

def test_create_player_ok(db, repo_mock):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.create_player.return_value = make_player(7)

    out = utils.create_player(db, 1, make_player_in())

    assert isinstance(out, schemas.PlayerOut)
    assert out.player_id == 7
    assert out.shirt_number == 10
    assert out.pacss_attributes.power == 60
    repo_mock.create_player.assert_called_once()


def test_create_player_pasa_los_datos_al_repository(db, repo_mock):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.create_player.return_value = make_player(7)
    player_in = make_player_in()

    utils.create_player(db, 1, player_in)

    repo_mock.create_player.assert_called_once_with(db, 1, player_in)


def test_create_player_usuario_inexistente(db, repo_mock):
    repo_mock.get_user.return_value = None

    with pytest.raises(schemas.UserNotFoundError):
        utils.create_player(db, 1, make_player_in())

    repo_mock.create_player.assert_not_called()


def test_get_behaviors_devuelve_solo_datos_publicos_y_codigo_vacio(db, repo_mock):
    behavior = SimpleNamespace(
        id_behavior=5, name="Defensa", python_code="print('secret')", is_default=False
    )
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_behaviors_by_creator.return_value = [behavior]

    behaviors = utils.get_behaviors(db, 1)

    assert behaviors == [
        schemas.BehaviorOut(
            id_behavior=5, name="Defensa", python_code="", is_default=False
        )
    ]
    repo_mock.get_behaviors_by_creator.assert_called_once_with(db, creator_id=1)


def test_get_behaviors_usuario_inexistente(db, repo_mock):
    repo_mock.get_user.return_value = None

    with pytest.raises(schemas.UserNotFoundError):
        utils.get_behaviors(db, 1)

    repo_mock.get_behaviors_by_creator.assert_not_called()


@pytest.mark.parametrize(
    "attrs",
    [dict(power=100, agility=100, control=100, speed=100, strength=100),  # suma 500
     dict(power=19, agility=61)],                                         # fuera de rango
)
def test_create_player_puntos_invalidos_no_toca_la_base(db, repo_mock, attrs):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)

    with pytest.raises(schemas.PointAssignmentError):
        utils.create_player(db, 1, make_player_in(**attrs))

    repo_mock.create_player.assert_not_called()
    
# ============================== get_players

def test_get_players_ok(db, repo_mock):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_players.return_value = [
        make_player(7, is_starter=True),
        make_player(8, is_starter=False),
    ]

    out = utils.get_players(db, 1)

    assert isinstance(out, list)
    assert len(out) == 2
    assert all(isinstance(p, schemas.PlayerOut) for p in out)
    assert [p.player_id for p in out] == [7, 8]
    repo_mock.get_players.assert_called_once_with(db, 1)


def test_get_players_lista_vacia(db, repo_mock):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_players.return_value = []

    out = utils.get_players(db, 1)

    assert out == []
    repo_mock.get_players.assert_called_once()


def test_get_players_usuario_inexistente(db, repo_mock):
    repo_mock.get_user.return_value = None

    with pytest.raises(schemas.UserNotFoundError):
        utils.get_players(db, 999)

    repo_mock.get_players.assert_not_called()


def test_get_players_hace_una_consulta_a_la_base(db, repo_mock):
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_players.return_value = [make_player(7)]

    utils.get_players(db, 1)

    repo_mock.get_players.assert_called_once_with(db, 1)

# ----------------- Friendly Matches -----------------
 
def make_friendly_match_in(team_name="Mi Equipo", match_duration=3, user_id=1):
    return schemas.FriendlyMatchCreate(
        user_id= user_id,          
        team_name=team_name,
        match_duration=match_duration,
    )

# ----------------- check_friendly_match_duration -----------------

@pytest.mark.parametrize("duration", [1, 2, 3, 4, 5])
def test_check_friendly_match_duration_ok(duration):
    utils.check_friendly_match_duration(duration)  # no lanza


@pytest.mark.parametrize("duration", [-2 , 6, 0, -1, 10])
def test_check_friendly_match_duration_invalida(duration):
    with pytest.raises(schemas.InvalidDurationError):
        utils.check_friendly_match_duration(duration)


# --------------------- check_friendly_team ---------------------

def test_check_friendly_team_ok():
    team = SimpleNamespace(
        team_id=1,
        players=[
            make_player(7, is_starter=True),
            make_player(8, is_starter=True),
            make_player(9, is_starter=True),
            make_player(10, is_starter=False),
        ]
    )
    assert utils.check_friendly_team(team) == 1


def test_check_friendly_team_no_existe():
    with pytest.raises(schemas.TeamNotFoundError):
        utils.check_friendly_team(None)


@pytest.mark.parametrize("starters_count", [0, 1, 2, 4])
def test_check_friendly_team_titulares_incorrectos(starters_count):
    team = SimpleNamespace(
        team_id=1,
        players=[make_player(i, is_starter=(i < starters_count + 7)) for i in range(7, 7 + starters_count)]
    )
    with pytest.raises(schemas.TeamIncompleteError):
        utils.check_friendly_team(team)


# --------------------- create_friendly_match ---------------------

@pytest.fixture
def repo_friendly(repo_mock):
    """Repository configurado para el camino optimo de create_friendly_match."""
    repo_mock.get_user.return_value = SimpleNamespace(id=1)
    repo_mock.get_team_by_owner_and_name.return_value = SimpleNamespace(
        team_id=1,
        players=[
            make_player(7, is_starter=True),
            make_player(8, is_starter=True),
            make_player(9, is_starter=True),
        ]
    )
    repo_mock.create_match.return_value = SimpleNamespace(match_id=10, is_friendly=True)
    return repo_mock


def test_create_friendly_match_ok(db, repo_friendly):
    result = utils.create_friendly_match(db, 1, make_friendly_match_in())

    assert result.match_id == 10
    assert result.is_friendly is True
    repo_friendly.create_match.assert_called_once()


def test_create_friendly_match_duracion_invalida_falla_rapido(db, repo_friendly):
    with pytest.raises(schemas.InvalidDurationError):
        utils.create_friendly_match(db, 1, make_friendly_match_in(match_duration=10))

    repo_friendly.get_user.assert_not_called()
    repo_friendly.create_match.assert_not_called()


def test_create_friendly_match_usuario_inexistente(db, repo_friendly):
    repo_friendly.get_user.return_value = None

    with pytest.raises(schemas.UserNotFoundError):
        utils.create_friendly_match(db, 1, make_friendly_match_in())

    repo_friendly.create_match.assert_not_called()


def test_create_friendly_match_equipo_inexistente(db, repo_friendly):
    repo_friendly.get_team_by_owner_and_name.return_value = None

    with pytest.raises(schemas.TeamNotFoundError):
        utils.create_friendly_match(db, 1, make_friendly_match_in())

    repo_friendly.create_match.assert_not_called()


def test_create_friendly_match_equipo_incompleto(db, repo_friendly):
    # Solo 2 titulares en lugar de 3
    repo_friendly.get_team_by_owner_and_name.return_value = SimpleNamespace(
        team_id=1,
        players=[
            make_player(7, is_starter=True),
            make_player(8, is_starter=True),
        ]
    )

    with pytest.raises(schemas.TeamIncompleteError):
        utils.create_friendly_match(db, 1, make_friendly_match_in())

    repo_friendly.create_match.assert_not_called()


def test_create_friendly_match_integrity_error_se_traduce(db, repo_friendly):
    repo_friendly.create_match.side_effect = IntegrityError("INSERT", {}, Exception("error"))

    with pytest.raises(schemas.CreateMatchError):
        utils.create_friendly_match(db, 1, make_friendly_match_in())

# ----------------- join_friendly_match -----------------

def make_match(status="open", away_team_id=None, owner_id=1, is_friendly=True,
               is_private=False, password=None):
    return SimpleNamespace(
        id_match=1, is_friendly=is_friendly, status=status,
        away_team_id=away_team_id, is_private=is_private, password=password,
        home_team=SimpleNamespace(owner_id=owner_id),
    )


def make_team(team_id=5, owner_id=2, starters=3):
    return SimpleNamespace(
        team_id=team_id, owner_id=owner_id,
        players=[make_player(i, is_starter=True) for i in range(1, starters + 1)],
    )


JOIN = schemas.JoinMatch(team_id=5)
PWD = "Secreta1!"
PRIVATE = make_match(is_private=True, password=utils.hash_password(PWD))


@pytest.fixture
def repo_join(repo_mock):
    """Camino feliz: partido open de usuario 1, equipo 5 del usuario 2 con 3 titulares."""
    repo_mock.get_match.return_value = make_match()
    repo_mock.get_team.return_value = make_team()
    repo_mock.join_match.return_value = SimpleNamespace(id_match=1, status="started", away_team_id=5)
    return repo_mock


def test_join_ok(db, repo_join):
    out = utils.join_friendly_match(db, 2, 1, JOIN)

    assert out.status == "started"
    assert out.away_team_id == 5
    repo_join.join_match.assert_called_once_with(db, match_id=1, away_team_id=5)


@pytest.mark.parametrize(
    "match, team, error",
    [
        (None, make_team(), schemas.MatchNotFoundError),
        (make_match(is_friendly=False), make_team(), schemas.MatchNotFoundError),
        (make_match(), None, schemas.TeamNotFoundError),
        (make_match(), make_team(owner_id=9), schemas.TeamNotAuthorizedError),
        (make_match(owner_id=2), make_team(), schemas.JoinOwnMatchError),
        (make_match(status="started", away_team_id=7), make_team(), schemas.MatchAlreadyTakenError),
        (make_match(status="finished"), make_team(), schemas.MatchNotJoinableError),
        (make_match(status="cancelled"), make_team(), schemas.MatchNotJoinableError),
        (make_match(), make_team(starters=2), schemas.TeamIncompleteError),
    ],
)
def test_join_rechazos(db, repo_join, match, team, error):
    repo_join.get_match.return_value = match
    repo_join.get_team.return_value = team

    with pytest.raises(error):
        utils.join_friendly_match(db, 2, 1, JOIN)

    repo_join.join_match.assert_not_called()


def test_join_reintento_del_mismo_equipo_es_idempotente(db, repo_join):
    match = make_match(status="started", away_team_id=5)
    repo_join.get_match.return_value = match

    assert utils.join_friendly_match(db, 2, 1, JOIN) is match
    repo_join.join_match.assert_not_called()


def test_join_pierde_la_carrera(db, repo_join):
    repo_join.join_match.return_value = None     # otro gano el UPDATE condicional

    with pytest.raises(schemas.MatchAlreadyTakenError):
        utils.join_friendly_match(db, 2, 1, JOIN)



def test_join_privado_con_password_correcta(db, repo_join):
    repo_join.get_match.return_value = PRIVATE

    utils.join_friendly_match(db, 2, 1, schemas.JoinMatch(team_id=5, password=PWD))

    repo_join.join_match.assert_called_once_with(db, match_id=1, away_team_id=5)


@pytest.mark.parametrize("password", [None, "", "Incorrecta1!"])
def test_join_privado_con_password_mala_o_ausente(db, repo_join, password):
    repo_join.get_match.return_value = PRIVATE

    with pytest.raises(schemas.MatchNotAuthorizedError):
        utils.join_friendly_match(db, 2, 1, schemas.JoinMatch(team_id=5, password=password))

    repo_join.join_match.assert_not_called()


def test_join_publico_ignora_la_password(db, repo_join):
    utils.join_friendly_match(db, 2, 1, schemas.JoinMatch(team_id=5, password="cualquiera"))

    repo_join.join_match.assert_called_once()


def test_join_privado_valida_la_password_antes_que_el_estado(db, repo_join):
    # un privado ya ocupado no debe revelar su estado a quien no tiene la password
    repo_join.get_match.return_value = make_match(
        status="started", away_team_id=7,
        is_private=True, password=utils.hash_password(PWD),
    )

    with pytest.raises(schemas.MatchNotAuthorizedError):
        utils.join_friendly_match(db, 2, 1, schemas.JoinMatch(team_id=5, password="mala"))