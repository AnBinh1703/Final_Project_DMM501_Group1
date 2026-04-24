# Contributing

This project is designed to be graded as an end-to-end ML system. Treat documentation, tests, and verification outputs as first-class deliverables.

## Official Team Roster

| Official member name | Declared delivery focus | Submission note |
|---|---|---|
| AN Duong Binh | Final integration, backend/API verification, testing, report ownership | Main author shown on the final report cover |
| Tuyen Le Quang | Deployment walkthrough | |
| NHI Nguyen Le Hong | Frontend UI/UX, demo ownership, report design | |    

## Git Evidence Visible in This Repository

The current clone exposes the following git author identities and contribution evidence:

| Git author identity | Commits in history | Representative evidence |
|---|---|---|
| Dương Bình An | 23 | Integration-test fixtures, dataset path handling, model loading/scoring tests, MLflow runtime tracking, frontend/API verification, report integration |
| Annwyn | 20 | Documentation expansion, benchmark summaries, CI coverage updates, deployment scripts, monitoring exporter, artifact refreshes, frontend/API system verification |

If official course-member names differ from git commit names or aliases, add a short mapping note with GitHub profile links or PR links before submission. This is important for the individual-contribution grading adjustment.

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
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts
MODEL_PATH=artifacts/models/final_model.joblib uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Run full stack (Docker Compose)
```bash
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts
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
- Contribution evidence preserved: meaningful commits, clear PR descriptions, and review comments tied to actual work

## Submission Hardening for Team Members

Before final submission, the team should prepare one short evidence pack per member:

- GitHub username and displayed commit name
- 2-4 representative pull requests or commits
- 1 short paragraph describing owned components
- 1 screenshot or terminal capture if the member owns demo/deployment work

This is the simplest way to defend the individual contribution adjustment during Q&A.

## CI/CD Notes

- `ci.yml` runs `pytest` with coverage gate.
- `docker.yml` validates Docker builds and Compose config.
