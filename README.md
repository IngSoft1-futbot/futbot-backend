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