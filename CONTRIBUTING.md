# Contributing

This project is designed to be graded as an end-to-end ML system. Treat documentation, tests, and verification outputs as first-class deliverables.

## Team Roles (Required for Submission)

Fill this table with the final team roster before submission.

| Member | Primary ownership | Secondary | Evidence (PRs/commits) |
|---|---|---|---|
| Name 1 | API + monitoring | tests | link to PRs |
| Name 2 | training + MLflow | Responsible AI | link to PRs |
| Name 3 | docs + deployment | frontend demo | link to PRs |

## Branching and PR Workflow

- Default branch: `main`
- Create feature branches: `feature/<short-name>` or `fix/<short-name>`
- Open PRs early; CI must be green before merging.
- Use meaningful commits (no “update”/“fix” only messages).

## Development Setup

### Python environment
```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install pytest-cov
```

### Run tests locally
```bash
pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Run API locally
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts
MODEL_PATH=artifacts/model.joblib uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Run full stack (Docker Compose)
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts
docker compose -f deployment/docker-compose.yml up --build
```

## Code Quality Expectations

- Keep code modular and testable; prefer pure functions where possible.
- Add tests for new behavior (unit first, then integration if needed).
- Avoid committing large binary artifacts; use `artifacts/` locally and document how to regenerate.

## PR Checklist

- Docs: `README.md` and/or `ARCHITECTURE.md` updated if behavior changed
- Tests: added/updated and passing locally
- Observability: metrics/alerts updated when introducing new endpoints or behaviors
- No secrets committed (`.env` must remain local)

## CI/CD Notes

- `ci.yml` runs `pytest` with coverage gate.
- `docker.yml` validates Docker builds and Compose config.
