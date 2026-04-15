# Model Benchmark Summary

- Dataset: `data/archive/creditcard.csv`
- Selected model (validation-only): **logistic_regression**
- Threshold policy: top-K rates (review/high) = 1.00% / 0.20%
- Thresholds (review/high): 0.74 / 1.00

## Final Test Metrics

- Review operating point (top-K): precision=0.1462, recall=0.8514
- High operating point (top-K): precision=0.8429, recall=0.7973
- PR-AUC (test): 0.7694
- ROC-AUC (test): 0.9652
