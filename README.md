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