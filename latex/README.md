# LaTeX Report (Submission)

Main file: `latex/FINAL_PROJECT_REPORT.tex`

Additional file (evidence-based E2E): `latex/FINAL_E2E_REPORT.tex`

Submission-style academic paper (required structure): `latex/EndToEnd_Fraud_Decision_Intelligence.tex`

## Build (PDF)

From repo root:

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_PROJECT_REPORT.tex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_PROJECT_REPORT.tex
```

Or for the evidence-based E2E report:

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_E2E_REPORT.tex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_E2E_REPORT.tex
```

Notes:
- The report includes images from `../artifacts/figures/*.png`. If those files are missing, run:
  - `python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42`
- If Matplotlib fails to write cache in restricted environments, set `MPLCONFIGDIR=/tmp` (as suggested in `QUICK_START.md`).

## Build (BibTeX paper)

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error EndToEnd_Fraud_Decision_Intelligence.tex
bibtex EndToEnd_Fraud_Decision_Intelligence
pdflatex -interaction=nonstopmode -halt-on-error EndToEnd_Fraud_Decision_Intelligence.tex
pdflatex -interaction=nonstopmode -halt-on-error EndToEnd_Fraud_Decision_Intelligence.tex
```
