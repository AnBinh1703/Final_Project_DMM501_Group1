# Responsible AI (RAI)

This project is a demo-grade ML system for fraud detection. The goal is to implement responsible practices that are feasible with the available dataset and system constraints, and to be explicit about limitations.

## 1) Fairness and Bias Analysis

### What “fairness” means in this context
Fraud detection decisions can cause harm when legitimate transactions are blocked (false positives) or fraud is missed (false negatives). Fairness here focuses on:

- consistent model performance across transaction “types” or segments
- avoiding systematic over-flagging of certain behavioral patterns

### Dataset limitations
The common credit card fraud dataset used for this project (when provided as `data/raw/creditcard.csv`) contains:

- anonymized PCA components `V1..V28`
- `Time` and `Amount`
- binary target `Class`

It does **not** include protected attributes (age, gender, ethnicity). That means:
- we cannot do demographic parity / equalized odds across protected groups
- fairness conclusions are limited to proxy slices (behavioral segments)

### Proxy slice checks (bias detection)
When running `src/pipelines/run_model_workflow.py`, the recommended slice checks are:
- **Amount buckets** (e.g., quantiles)
- **Time buckets** (e.g., hour-of-day derived from `Time` seconds)

For each slice, compute and compare:
- PR-AUC and ROC-AUC (when slice size supports it)
- precision/recall at the chosen operating threshold
- fraud rate (base rate) to contextualize results

**Interpretation**:
- Large performance gaps across slices can indicate bias or data coverage issues.
- If a slice has very few positive samples, metrics are unstable; treat as “insufficient evidence”, not as a claim of fairness.

### Mitigations used in this repo
- Class imbalance handling:
  - baseline models use `class_weight="balanced"` (where applicable)
  - threshold tuning uses validation data to choose an operating point explicitly
- Monitoring:
  - prediction rate and latency alerts to catch system regressions and operational drift

## 2) Explainability

### Approach
This project uses SHAP for model explainability (global feature importance) in the benchmarking workflow:
- `src/pipelines/run_model_workflow.py` generates:
  - `artifacts/figures/shap_summary.png`
  - `artifacts/benchmarks/shap_importance_table.csv`

### What SHAP does and does not provide
- Provides: which features contribute most to model outputs on average.
- Does not provide: causal explanations; guarantees about fairness; explanations for unseen distributions.

### Operational use
For compliance/audit, the SHAP summary plot and importance table can be attached to a model version and archived with the release notes.

## 3) Privacy Considerations

### Data minimization
- The real dataset’s PCA features are anonymized; raw merchant/customer identifiers are not present.
- The API accepts a numeric feature vector only; it does not require PII.

### Logging stance (recommended)
- Do not log raw feature vectors in production.
- Log only:
  - request_id
  - model_version
  - latency and status code
  - score summary statistics (aggregated)

### Data retention
- Keep training data outside the repo.
- Keep model artifacts and reports (`artifacts/`) reproducible from scripts, not manually edited.

## 4) Ethical Risks

### Primary harms
- **False positives**: legitimate transactions flagged or blocked, causing customer frustration and lost sales.
- **False negatives**: fraud missed, causing financial loss.

### Threshold policy
The decision threshold is an explicit business choice:
- Lower threshold increases recall but increases false positives.
- Higher threshold reduces false positives but may miss fraud.

The training pipeline records the chosen threshold in `model_info.json` to avoid hidden policy changes.

### Human-in-the-loop (recommended operational pattern)
- Use `fraud_probability` as a prioritization signal.
- Use tiered actions:
  - low risk: allow
  - medium: step-up authentication / review
  - high: block + manual review

## Mitigations and Residual Risks

| Risk | Mitigation in this project | Residual risk / limitation | Owner |
|---|---|---|---|
| Feature mismatch at inference | Enforce `n_features` from metadata; return 422 on mismatch | Does not validate semantic feature order | API owner |
| Bias across behavior segments | Recommend slice metrics by Amount/Time; document limitations | No protected attributes; proxy slices only | ML owner |
| Privacy leakage via logs | Document “no raw features in logs” policy | Depends on deployment configuration | Platform owner |
| Over-trusting explanations | Document SHAP limitations | SHAP is not causal | ML owner |
| Concept drift | Monitor prediction rate/latency; document drift as future work | No drift detection/retrain automation | Team |
