from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import pytest
import jwt
from sqlalchemy.exc import IntegrityError

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


#-------------------------------------Crear Equipo-----------------------------------------------

def make_player(pid, owner_id=1, team_id=None, behavior_id=0, is_starter=None):
    return SimpleNamespace(player_id=pid, owner_id=owner_id, team_id=team_id,
                           name=f"Jugador {pid}", behavior_id=behavior_id, is_starter=is_starter)


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


def test_create_team_jugador_repetido(db, repo_team):
    with pytest.raises(schemas.PlayerAlreadyInUseError):
        utils.create_team(db, 1, make_team_in((7, 8, 9), (9, 11, 12)))

    repo_team.add_team.assert_not_called()


def test_create_team_usuario_inexistente(db, repo_team):
    repo_team.get_user.return_value = None

    with pytest.raises(schemas.UserNotFoundError):
        utils.create_team(db, 1, make_team_in())

    repo_team.add_team.assert_not_called()


def test_create_team_jugador_inexistente(db, repo_team):
    repo_team.get_players_by_ids.return_value = [make_player(i) for i in range(7, 12)]  # falta el 12

    with pytest.raises(schemas.PlayerNotFoundError):
        utils.create_team(db, 1, make_team_in())

    repo_team.add_team.assert_not_called()


def test_create_team_jugador_de_otro_usuario(db, repo_team):
    players = [make_player(i) for i in range(7, 12)] + [make_player(12, owner_id=2)]
    repo_team.get_players_by_ids.return_value = players

    with pytest.raises(schemas.PlayerNotAuthorizedError):
        utils.create_team(db, 1, make_team_in())

    repo_team.add_team.assert_not_called()


def test_create_team_jugador_ya_en_otro_equipo(db, repo_team):
    players = [make_player(i) for i in range(7, 12)] + [make_player(12, team_id=3)]
    repo_team.get_players_by_ids.return_value = players

    with pytest.raises(schemas.PlayerAlreadyInUseError):
        utils.create_team(db, 1, make_team_in())

    repo_team.add_team.assert_not_called()


def test_create_team_behavior_inexistente(db, repo_team):
    repo_team.get_behaviors_by_ids.return_value = []

    with pytest.raises(schemas.BehaviorNotFoundError):
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
