.PHONY: help install test test-unit test-integration test-local-e2e lint run-api

help:
	@echo "Targets: install, test, test-unit, test-integration, test-local-e2e, run-api"

install:
	pip install -r requirements.txt

test:
	pytest -q

test-unit:
	pytest -q tests/unit tests/data

test-integration:
	pytest -q tests/integration

test-local-e2e:
	python tests/test_frontend_api.py
	python tests/verify_system.py

run-api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000
