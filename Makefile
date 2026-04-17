SHELL := /bin/bash
ROOT_DIR := $(shell pwd)
BACKEND_DIR := $(ROOT_DIR)/apps/backend
FRONTEND_DIR := $(ROOT_DIR)/apps/frontend
ANSIBLE_ENV := ANSIBLE_LOCAL_TEMP=$(ROOT_DIR)/.ansible-tmp ANSIBLE_REMOTE_TMP=$(ROOT_DIR)/.ansible-tmp XDG_CACHE_HOME=$(ROOT_DIR)/.cache ANSIBLE_HOME=$(ROOT_DIR)/.ansible-home ANSIBLE_GALAXY_CACHE_DIR=$(ROOT_DIR)/.ansible-home/galaxy_cache

.PHONY: bootstrap up down lint test test-backend test-ansible test-frontend seed demo

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
