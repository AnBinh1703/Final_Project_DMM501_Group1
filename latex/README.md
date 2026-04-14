# LaTeX Report (Submission)

Main file: `latex/FINAL_PROJECT_REPORT.tex`

## Build (PDF)

From repo root:

```bash
cd latex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_PROJECT_REPORT.tex
pdflatex -interaction=nonstopmode -halt-on-error FINAL_PROJECT_REPORT.tex
```

Notes:
- The report includes images from `../artifacts/figures/*.png`. If those files are missing, run:
  - `python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42`
- If Matplotlib fails to write cache in restricted environments, set `MPLCONFIGDIR=/tmp` (as suggested in `QUICK_START.md`).

