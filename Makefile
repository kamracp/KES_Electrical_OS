# KES Electrical OS — developer entry points. Run from the repository root.
.PHONY: help backend-dev frontend-dev check-backend check-frontend gate health deploy

help:
	@echo "make backend-dev     run API on :8012 (dev)"
	@echo "make frontend-dev    run Vite on :5173"
	@echo "make check-backend   ruff format/lint + pytest"
	@echo "make check-frontend  typecheck + oxlint + vitest + build"
	@echo "make gate            full regression (backend + frontend)"
	@echo "make health          health check against dev backend"
	@echo "make deploy          release gate + deploy to Lightsail (needs ~/.keos-deploy.env)"

backend-dev:
	.venv/bin/uvicorn app.main:app --app-dir backend --port 8012 --reload

frontend-dev:
	cd frontend && npm run dev

check-backend:
	scripts/check_backend.sh

check-frontend:
	scripts/check_frontend.sh

gate:
	scripts/full_regression.sh

health:
	scripts/healthcheck.sh http://127.0.0.1:8012

deploy:
	scripts/deploy.sh
