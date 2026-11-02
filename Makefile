.PHONY: up down migrate seed dev-api dev-web test test-dev3 lint typecheck \
        import-check eval demo-reset smoke replay

# ── Infrastructure ────────────────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "Waiting for Postgres to be ready..."
	@docker compose exec db sh -c "until pg_isready -U proofpay; do sleep 1; done"

down:
	docker compose down

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migrate-fresh:
	alembic downgrade base && alembic upgrade head

# ── Data ──────────────────────────────────────────────────────────────────────
seed:
	python scripts/seed.py

demo-reset:
	python backend/scripts/demo_reset.py

eval:
	python backend/scripts/run_eval.py

# ── Dev servers ───────────────────────────────────────────────────────────────
dev-api:
	uvicorn backend.app.main:app --reload --port 8000

dev-web:
	cd web && npm run dev

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	pytest backend/tests -v --tb=short

test-dev3:
	pytest backend/tests -v --tb=short

test-unit:
	pytest backend/tests/unit -v --tb=short

test-scenarios:
	pytest backend/tests/scenarios -v --tb=short

smoke:
	pytest backend/tests -v -k "smoke" -x --tb=short

replay:
	python backend/scripts/replay_event.py $(EVENT)

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	ruff check . && ruff format --check .

lint-fix:
	ruff check --fix . && ruff format .

typecheck:
	mypy backend/app/contracts backend/app/policy --strict

import-check:
	lint-imports

ci: lint import-check test
