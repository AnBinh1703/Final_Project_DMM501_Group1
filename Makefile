.PHONY: help install test lint run-api

help:
	@echo "Targets: install, test, run-api"

install:
	pip install -r requirements.txt

test:
	pytest -q

run-api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000
