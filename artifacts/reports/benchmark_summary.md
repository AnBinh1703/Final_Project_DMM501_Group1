# Model Benchmark Summary

- Dataset: `data/archive/creditcard.csv`
- Baseline tuned threshold: 0.99
- Improved tuned threshold: 0.84
- Selected model: **logistic_regression**

## Tuned Metrics (CSV)

```csv
model,threshold,precision,recall,f1,roc_auc,pr_auc
logistic_regression,0.99,0.6741573033707865,0.8108108108108109,0.7361963190184049,0.9679722632029891,0.7928733741399766
lightgbm,0.8400000000000001,0.8852459016393442,0.7297297297297297,0.8,0.8828017663133026,0.7160881657535132
```
