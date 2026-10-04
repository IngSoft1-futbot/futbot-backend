# FUTBOT -- BACKEND
## Makefile
Se agrego un makefile para facilitar el levante de la base de datos y backend.
### Requisitos:
* **make**
* **Docker**
### Comandos
* **make help:**	Lista los comandos
* **make install:**	Crea el venv e instala las dependencias
* **make dev:**	Levanta base, crea tablas y arranca el backend
* **make run:**	Solo el backend (la base ya debe estar arriba)
* **make db:**	Levanta el contenedor de Postgres
* **make init-db:**	Crea las tablas que falten
* **make reset-db:**	Borra las tablas y las recrea
* **make stop-db:**	Apaga Postgres sin perder datos
* **make psql:**	Consola SQL dentro de la base
* **make test:**	Corre pytest

### Flujo habitual
```
make install    # una sola vez
make dev        # cada día para trabajar
make test       # antes de subir cambios
```
## Registrar usuario
POST /auth/register crea un usuario con contraseña hasheada (bcrypt) y email en minusculas. El club es un campo unico del usuario (club, reemplaza a username). No se crea un Team en el registro.

### Capas (cada una llama a la de abajo)
**Archivo Responsabilidad**
**app.py Endpoint:** traduce excepciones a codigos HTTP
**utils.py Logica:** validar contraseña, chequear duplicados, hashear
**product_repository.py**	Queries y commit/rollback, sin logica
**models.py / database.py:**	Tablas, engine y sesion (get_db)
**schemas.py:**	Validacion estructural (Pydantic) y excepciones
**responses.py:**	Documentacion de errores para Swagger
**Respuesta:**
Codigo	Cuando	detail
201	Registro exitoso	UserOut (sin contraseña)
400	Email en uso	Email already in use.
400	Club en uso	Club already in use.
400	Contraseña invalida	Mensaje de la regla incumplida
409	Duplicado simultaneo	Conflict in register time.
422	Campo faltante o estructura invalida	Lista de Pydantic
### Reglas
**Contraseña:** 8 a 12 caracteres, sin espacios, con mayuscula, minuscula, numero y simbolo.
**Club:** 3 a 50 caracteres. Name: 1 a 20. Ambos se recortan.
**avatar** es opcional.
### Tests
|           Archivo            |       Prueba       |        Base         |
|------------------------------|--------------------|---------------------|
|**test_schemas.py**           | Estructura         | Ninguna             |
|**test_utils.py**	           | Logica	            | Repository mockeado |
|**test_app.py**	           | Traduccion a HTTP  | Utils mockeado      |
|**test_product_repository.py**| Queries y unique   | SQL en memoria      |



## Iniciar sesion
`POST /auth/login/` Autentica a un usuario existente validando sus credenciales (correo electronico y contraseña) y retorna un token de acceso de tipo Bearer. Por motivos de consistencia, el correo electronico se procesa y normaliza automaticamente a minusculas antes de realizar la busqueda en la base de datos, asegurando coincidencia exacta con el registro.

Para utilizar la funcion get_current_user_id en cualquier otro endpoint de el proyecto que requiera autenticacion, tienen que inyectarla como una dependencia de FastAPI usando Depends(), como parametro dentro de la definicion de la funcion del endpoint
Ejemplo: current_user_id: int = Depends(get_current_user_id)

### Respuesta:
| Codigo | Cuando | Detail / Mensaje |
| :--- | :--- | :--- |
| **200** | Login exitoso | `status: "200"`, `data: { access_token, token_type }`, `message: "Login successful."` |
| **401** | Credenciales invalidas | `status: "401 Unauthorized"`, `message: "Invalid email or password."` |
| **422** | Estructura invalida | Lista de errores de Pydantic |

## Crear equipo

`POST /users/{user_id}/teams` Crea un equipo con 3 titulares y 3 suplentes, cada uno con su behavior, y lo devuelve con los jugadores separados en titulares y suplentes. Requiere token Bearer y el `user_id` de la ruta tiene que ser el del usuario autenticado.

### Payload
```json
{
  "name": "Mi Equipo",
  "jugadores_titulares": [
    {"player_id": 7, "behavior_id": 5},
    {"player_id": 8},
    {"player_id": 9}
  ],
  "jugadores_suplentes": [
    {"player_id": 10},
    {"player_id": 11},
    {"player_id": 12}
  ]
}
```

* player_id: jugadores del usuario que todavia no tienen equipo.
* behavior_id: opcional. El jugador 7 usa el behavior 5 (propio del usuario); los demas no lo envian y reciben el default (id 0).
### Recorrido
1. **app.py**: Pydantic valida el body (422 si esta mal), se valida el token (401) y se compara el id del token con el user_id de la ruta (403).
2. **utils.py** (create_team), en este orden:
    * Plantel de exactamente 3 titulares y 3 suplentes, sin player_id repetidos.
    * El usuario existe.
    * Los behaviors sin elegir pasan a ser el default (0).
    * Los jugadores existen, son del usuario y no tienen equipo.
    * Los behaviors existen y son del usuario (el default es de todos).
    * El usuario no tiene otro equipo con ese nombre.
3. **product_repository.py** (add_team): crea el equipo y asigna team_id, behavior_id e is_starter a cada jugador en un solo commit. Si algo falla hace rollback, asi que nunca queda un equipo a medias.
4. **utils.py** (build_team_out) separa titulares y suplentes y app.py responde 201.
### Respuesta:
|Codigo |Cuando                                              |detail                                                                                                              |
|-------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
|  201  |  Equipo creado	                                 |  TeamOut: team_id, name, jugadores_titulares, jugadores_suplentes (cada jugador con player_id, name, behavior_id)  |
|  400  |  No son 3 titulares y 3 suplentes	                 |  Team incomplete, must be 3 starters & 3 subtitutes.                                                               |
|  400  |  player_id repetido o jugador que ya tiene equipo  |  Some players are already in use.                                                                                  |
|  400  |  Nombre de equipo repetido para el usuario	     |  Team name already in use for this user.                                                                           |
|  401  |  Token invalido	                                 |  Could not validate credentials.                                                                                   |
|  403  |  user_id distinto del usuario autenticado	         |  Not allowed to create teams for another user.                                                                     |
|  403  |  Jugador o behavior de otro usuario	             |  User is not the owner of the player. / User is not the owner of the behavior.                                     |
|  404  |  Usuario, jugador o behavior inexistente	         |  User can not find. / Player can not find. / Behavior can not find.                                                |
|  409  |  Duplicado simultaneo al guardar	                 |  Conflict in creation time.                                                                                        |
|  422  |  Campo faltante o estructura invalida	             |  Lista de Pydantic.                                                                                             |

### Reglas

**Nombre**: 3 a 30 caracteres, unico por usuario. 
**Plantel**: 3 titulares y 3 suplentes, sin repetidos. Un jugador solo puede estar en un equipo. 
**Behavior**: opcional; sin behavior se usa el default (id 0).

## Crear jugador

`POST /users/{user_id}/players` Crea un jugador con atributos PACSS (Power, Agility, Control, Speed, Strength) que suman exactamente 300 puntos, cada uno entre 20 y 100. El jugador se asigna al usuario autenticado y recibe un behavior_id por defecto (0). Requiere token Bearer y el `user_id` de la ruta tiene que ser el del usuario autenticado.

### Payload
```json
{
  "name": "Lionel Messi",
  "shirt_number": 10,
  "pacss_attributes": {
    "power": 60,
    "agility": 80,
    "control": 75,
    "speed": 70,
    "strength": 15
  }
}
```

* name: nombre del jugador (requerido).
* shirt_number: número de camiseta 0-99 (requerido).
* pacss_attributes: objeto con los 5 atributos. Cada uno entre 20 y 100, suma total exactamente 300 (requerido).

### Recorrido
1. **app.py**: Pydantic valida el body (422 si está mal), se valida el token (401) y se compara el id del token con el user_id de la ruta (403).
2. **utils.py** (create_player):
    * El usuario existe.
    * Los puntos PACSS suman exactamente 300 y cada atributo está en [20, 100].
3. **product_repository.py** (create_player): inserta el jugador en la base de datos con owner_id, behavior_id default (0) e is_starter false.
4. **utils.py** (build_player_out) convierte el objeto ORM plano a PlayerOut con pacss_attributes anidado, y app.py responde 201.

### Respuesta:
| Código | Cuando | detail |
| :--- | :--- | :--- |
| **201** | Jugador creado | PlayerOut: player_id, name, shirt_number, behavior_id, pacss_attributes, team_id |
| **400** | Puntos PACSS inválidos | Points must total 300, each between 20 and 100. |
| **401** | Token inválido | Could not validate credentials. |
| **403** | user_id distinto del usuario autenticado | Not allowed to players for another user. |
| **404** | Usuario inexistente | User could not be found. |
| **422** | Campo faltante o estructura inválida | Lista de Pydantic. |

### Reglas

**Nombre**: requerido, sin límite de largo (se valida en schemas si lo deseas).
**Número de camiseta**: 0-99, requerido.
**PACSS**: cada atributo entre 20 y 100 inclusive, suma total = 300. Los 5 atributos son obligatorios.
**Propietario**: el jugador pertenece al usuario que hace la request; solo ese usuario puede usarlo en equipos.
**Comportamiento**: todo jugador nuevo recibe behavior_id = 0 (default); puede cambiar cuando se asigna a un equipo.
**Equipo**: inicialmente null; se asigna cuando se crea un equipo que incluya al jugador.


## Crear partido amistoso

`POST /users/{user_id}/friendly-matches` Crea un partido amistoso y lo deja en estado "open" (esperando rival) utilizando un equipo especifico del creador como equipo local (`home_team`). Requiere token Bearer. Para evitar manipulaciones, el `user_id` autenticado en el token, el de la ruta URL y el provisto en el JSON deben coincidir exactamente.

### Payload
```json
{
  "user_id": 1,
  "team_name": "Mi Equipo",
  "match_duration": 3
}
```
.user_id: ID del usuario creador (debe coincidir con la URL).
.team_name: Nombre exacto del equipo local (debe pertenecer al usuario).
.match_duration: Duración de cada cuarto del partido en minutos (estrictamente entre 1 y 5).

### Recorrido

1.**app.py**: Pydantic valida la estructura de los datos (422 si falta un campo o tipo). Verifica   que el token sea válido (401). Confirma que el creador autenticado coincida con la ruta URL (403) y con el user_id enviado en el cuerpo de la petición (400).

2.utils.py (create_friendly_match):

  -Verifica que el usuario exista en la base de datos.

  -Busca el equipo usando el team_name y asegurando que pertenezca al user_id.

  -Valida la regla de negocio de la duración por cuarto (1 a 5 minutos).

  -Chequea la integridad del equipo local, exigiendo que tenga exactamente 3 jugadores titulares.

3.product_repository.py (create_match): Inserta el registro en la tabla matches forzando los valores automáticos para un amistoso público (is_friendly=True, status="open", away_team_id=None, is_private=False, password=None). Si hay un error de base de datos, hace rollback.

4.app.py: Retorna un código HTTP 201 devolviendo los detalles completos del partido creado.

### Respuesta:

Código	  Cuando	  detail
201	  Partido creado	  FriendlyMatchOut: id_match, is_friendly, status, home_team_id, away_team_id, match_duration, etc.
400	  Mismatch de User ID	  User ID in body does not match User ID in path.
400	  Duración fuera de rango	  Match duration must be between 1 and 5 minutes.
400	  Equipo sin 3 titulares	  Team incomplete, must have exactly 3 starters.
401	  Token inválido / ausente	  Could not validate credentials.
403	  Crear a nombre de otro	  Not allowed to create matches for another user.
404	  Usuario no existe	User not found.
404	  Equipo ajeno o no existe	  Team not found or does not belong to the user.
409	  Duplicado / Conflicto DB	  Conflict in match creation.
422	  Estructura inválida	  Lista de Pydantic.


### Reglas

-Duracion: Estrictamente limitada a valores entre 1 y 5 minutos por cuarto (enviado a traves del campo match_duration).

-Estado inicial: Todo amistoso nace con estado open y con el equipo visitante (away_team_id) vacio, esperando que otro jugador se una a la sala.

-Validacion de Plantel: No basta con que el equipo exista, se verifica activamente en el momento de creacion del partido que el equipo cuente de manera integra con sus 3 jugadores titulares listos para jugar.

-Detalle: esta implementacion tiene en consideracion solo que los amistosos sean publicos, en proximas actualizaciones se podra incluir distincion entre amistosos publicos y privados

## Listar partidos amistosos
`GET /friendlymatches` Devuelve los partidos amistosos disponibles, es decir, los que estan abiertos esperando a otro jugador. Es una ruta publica: no requiere token ni recibe parametros.

### Recorrido
1. **app.py** llama a `utils.get_available_friendly_matches`.
2. **utils.py** pide la lista al repository. Si la base falla, convierte el error en `FriendlyMatchesError`.
3. **product_repository.py** (`get_open_friendly_matches`) consulta los `Match` con `is_friendly = true` y `status = "open"`, ordenados por `id_match`.
4. **app.py** serializa cada partido con `FriendlyMatchOut` y responde 200. Si recibe `FriendlyMatchesError`, responde 500.

### Respuesta:
| Codigo | Cuando | Contenido |
| :--- | :--- | :--- |
| **200** | Consulta exitosa | Lista de `FriendlyMatchOut` (vacia si no hay amistosos disponibles) |
| **500** | Error al consultar la base | `detail: "Internal Server Error"` |

Cada elemento de la lista:
```
{
  "id_match": 1,
  "home_team_id": 3,
  "match_duration": 10,
  "is_private": false
}
```

### Reglas
**Disponible:** amistoso (`is_friendly`) con `status` abierto. Los que ya empezaron, terminaron o se cancelaron no aparecen, y tampoco los partidos de liga.
**Privados:** aparecen en el listado con `is_private: true`. La contraseña nunca se devuelve; se valida al unirse al partido.
**Duracion:** `match_duration` es la duracion propia del amistoso, en minutos.

### Tests
Cada capa prueba lo suyo: schemas (`FriendlyMatchOut` desde el objeto de la base), repository (el filtro, con SQLite en memoria), utils (traduccion del error de la base) y app (200, lista vacia, 500 y que no se exponga la contraseña).