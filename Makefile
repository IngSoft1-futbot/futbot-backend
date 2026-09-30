# Makefile de futbot-backend
# Uso: make help

VENV         := venv
PY           := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
UVICORN      := $(VENV)/bin/uvicorn

DB_CONTAINER := futbot-db
DB_USER      := postgres
DB_PASSWORD  := postgres
DB_NAME      := futbot
DB_PORT      := 5432

.DEFAULT_GOAL := help
.PHONY: help install db wait-db init-db run dev stop-db reset-db psql test

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

install: ## Crea el venv (si no existe) e instala dependencias
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install fastapi uvicorn sqlalchemy psycopg2-binary email-validator bcrypt pytest httpx2

db: ## Levanta el contenedor de Postgres (lo crea si no existe)
	@docker start $(DB_CONTAINER) >/dev/null 2>&1 || \
		docker run --name $(DB_CONTAINER) \
			-e POSTGRES_USER=$(DB_USER) \
			-e POSTGRES_PASSWORD=$(DB_PASSWORD) \
			-e POSTGRES_DB=$(DB_NAME) \
			-p $(DB_PORT):5432 -d postgres
	@echo "Postgres levantado en localhost:$(DB_PORT)"

wait-db: ## Espera a que Postgres acepte conexiones
	@echo "Esperando a Postgres..."
	@until docker exec $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME) -c "SELECT 1" >/dev/null 2>&1; do sleep 1; done
	@echo "Postgres listo."

init-db: ## Crea las tablas que falten (no modifica las existentes)
	$(PY) -c "from src.database import init_db; init_db()"

run: ## Levanta solo el backend (la base debe estar arriba)
	$(UVICORN) src.app:app --reload

dev: db wait-db init-db ## Levanta base + tablas + backend (todo junto)
	$(UVICORN) src.app:app --reload

stop-db: ## Apaga el contenedor de Postgres (conserva los datos)
	docker stop $(DB_CONTAINER)

reset-db: db wait-db ## BORRA todas las tablas y las recrea con el esquema actual
	$(PY) -c "from src.database import Base, engine; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"
	@echo "Tablas recreadas."

psql: ## Abre una consola SQL dentro de la base
	docker exec -it $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME)

test: ## Corre los tests con pytest
	$(VENV)/bin/pytest -v