# Geek-Trainer. See PLAN.md for what each stage is for.
.PHONY: help devdb devdb-stop migrate revision seed api web dev test test-api typecheck build

PY := api/.venv/bin/python
PIP := api/.venv/bin/pip
DBURL = $(shell cd api && $(CURDIR)/$(PY) scripts/devdb.py url)

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  %-14s %s\n", $$1, $$2}'

devdb: ## start the local Postgres (pgserver wheel; no Docker, no sudo)
	@cd api && ../$(PY) scripts/devdb.py start

devdb-stop: ## stop it
	@cd api && ../$(PY) scripts/devdb.py stop

migrate: ## apply migrations to the dev database
	@cd api && DATABASE_URL="$$(../$(PY) scripts/devdb.py url)" ../api/.venv/bin/alembic upgrade head

revision: ## autogenerate a migration: make revision m="what changed"
	@cd api && DATABASE_URL="$$(../$(PY) scripts/devdb.py url)" ../api/.venv/bin/alembic revision --autogenerate -m "$(m)"

api: ## run the API on :8000
	@cd api && DATABASE_URL="$$(../$(PY) scripts/devdb.py url)" ../api/.venv/bin/uvicorn app.main:app --reload --port 8000

seed: ## load the seed exercise catalogue
	@cd api && DATABASE_URL="$$(../$(PY) scripts/devdb.py url)" ../$(PY) scripts/seed.py

web: ## run the web app on :3000 (proxies /api to :8000)
	@cd web && npm run dev

dev: ## everything: database, migrations, seed, API and web
	@$(MAKE) devdb migrate seed
	@echo "starting API on :8000 and web on :3000 - open http://localhost:3000"
	@cd api && DATABASE_URL="$$(../$(PY) scripts/devdb.py url)" ../api/.venv/bin/uvicorn app.main:app --port 8000 & \
	 cd web && npm run dev

test: test-api ## run everything

test-api: ## backend tests (spins up its own Postgres)
	@cd api && ../$(PY) -m pytest -q

typecheck: ## typecheck the web app
	@cd web && npm run typecheck

build: ## production build of the web app
	@cd web && npm run build
