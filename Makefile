SHELL := /bin/bash
ROOT_DIR := $(shell pwd)
BACKEND_DIR := $(ROOT_DIR)/apps/backend
FRONTEND_DIR := $(ROOT_DIR)/apps/frontend
ANSIBLE_ENV := ANSIBLE_LOCAL_TEMP=$(ROOT_DIR)/.ansible-tmp ANSIBLE_REMOTE_TMP=$(ROOT_DIR)/.ansible-tmp XDG_CACHE_HOME=$(ROOT_DIR)/.cache ANSIBLE_HOME=$(ROOT_DIR)/.ansible-home ANSIBLE_GALAXY_CACHE_DIR=$(ROOT_DIR)/.ansible-home/galaxy_cache

.PHONY: bootstrap up down lint test test-backend test-ansible test-frontend seed demo run-backend run-frontend run-servicenow run-dev up-local up-all up-local-backend up-local-frontend up-local-servicenow up-individual stop-local show-ports show-port-backend show-port-frontend show-port-servicenow

bootstrap:
	cp -n .env.example .env || true
	python3 scripts/seed_data.py

up:
	docker compose up --build -d

down:
	docker compose down -v

lint:
	mkdir -p $(ROOT_DIR)/.ansible-tmp $(ROOT_DIR)/.cache $(ROOT_DIR)/.ansible-home/galaxy_cache
	cd $(ROOT_DIR) && pytest tests/backend tests/integration tests/orchestrator -q
	cd $(ROOT_DIR) && $(ANSIBLE_ENV) ansible-lint ansible/playbooks
	cd $(ROOT_DIR) && $(ANSIBLE_ENV) yamllint ansible

test: test-backend test-ansible

test-backend:
	cd $(ROOT_DIR) && pytest -q

test-ansible:
	cd $(ROOT_DIR) && pytest -q tests/ansible/test_ansible_validation.py

test-frontend:
	cd $(FRONTEND_DIR) && npm test -- --run

seed:
	python3 scripts/seed_data.py

demo:
	bash scripts/demo_scenarios.sh

run-backend:
	@$(MAKE) --no-print-directory show-port-backend
	bash scripts/run_backend.sh

run-frontend:
	@$(MAKE) --no-print-directory show-port-frontend
	bash scripts/run_frontend.sh

run-servicenow:
	@$(MAKE) --no-print-directory show-port-servicenow
	bash scripts/run_servicenow_sim.sh

up-all:
	@$(MAKE) --no-print-directory show-ports
	bash scripts/run_dev_stack.sh

# Friendly aliases for local runtime
up-local: up-all

run-dev:
	@echo "[legacy] make run-dev is kept for compatibility. Prefer: make up-all"
	@$(MAKE) --no-print-directory up-all

up-local-backend: run-backend

up-local-frontend: run-frontend

up-local-servicenow: run-servicenow

up-individual:
	@$(MAKE) --no-print-directory show-ports
	@echo "Start in 3 terminals:"
	@echo "  make up-local-servicenow"
	@echo "  make up-local-backend"
	@echo "  make up-local-frontend"

stop-local:
	@source scripts/lib/load_env.sh; load_env_file .env; \
	FRONTEND_PORT="$${FRONTEND_PORT:-13000}"; \
	PIDS=""; \
	PIDS="$$PIDS $$(pgrep -f 'uvicorn app.main:app' || true)"; \
	PIDS="$$PIDS $$(pgrep -f 'uvicorn services.servicenow_sim.api:app' || true)"; \
	PIDS="$$PIDS $$(pgrep -f \"next dev --hostname .* --port $$FRONTEND_PORT\" || true)"; \
	PIDS="$$(echo $$PIDS | xargs -n1 | sort -u | xargs)"; \
	if [ -n "$$PIDS" ]; then \
		echo "Stopping local dev processes: $$PIDS"; \
		kill $$PIDS; \
	else \
		echo "No local dev processes found."; \
	fi

show-port-backend:
	@source scripts/lib/load_env.sh; load_env_file .env; \
	BACKEND_HOST="$${BACKEND_HOST:-0.0.0.0}"; \
	BACKEND_PORT="$${BACKEND_PORT:-18010}"; \
	echo "AFL Backend -> bind=$$BACKEND_HOST:$$BACKEND_PORT | docs=http://127.0.0.1:$$BACKEND_PORT/docs"

show-port-frontend:
	@source scripts/lib/load_env.sh; load_env_file .env; \
	FRONTEND_HOST="$${FRONTEND_HOST:-0.0.0.0}"; \
	FRONTEND_PORT="$${FRONTEND_PORT:-13000}"; \
	BACKEND_PORT="$${BACKEND_PORT:-18010}"; \
	NEXT_PUBLIC_API_BASE_URL="$${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:$$BACKEND_PORT}"; \
	echo "AFL Frontend -> bind=$$FRONTEND_HOST:$$FRONTEND_PORT | url=http://127.0.0.1:$$FRONTEND_PORT/ | api=$$NEXT_PUBLIC_API_BASE_URL"

show-port-servicenow:
	@source scripts/lib/load_env.sh; load_env_file .env; \
	SERVICENOW_SIM_HOST="$${SERVICENOW_SIM_HOST:-0.0.0.0}"; \
	SERVICENOW_SIM_PORT="$${SERVICENOW_SIM_PORT:-18095}"; \
	AFL_BACKEND_BASE_URL="$${AFL_BACKEND_BASE_URL:-http://127.0.0.1:18010}"; \
	echo "ServiceNow Sim -> bind=$$SERVICENOW_SIM_HOST:$$SERVICENOW_SIM_PORT | portal=http://127.0.0.1:$$SERVICENOW_SIM_PORT/ | AFL connector=$$AFL_BACKEND_BASE_URL"

show-ports:
	@$(MAKE) --no-print-directory show-port-servicenow
	@$(MAKE) --no-print-directory show-port-backend
	@$(MAKE) --no-print-directory show-port-frontend
