# Responsible AI

## Scope

This project provides fraud decision-support capabilities, not autonomous irreversible fraud adjudication.

Outputs are intended to support analyst workflow and policy-driven interventions.

## 1. Score Semantics and Truthfulness

- `risk_score` is exposed as `risk_score_uncalibrated`.
- The system does not claim calibrated fraud probability.
- API responses include explicit score semantics and thresholds to reduce misuse.

## 2. Decision and Human Oversight

Implemented decisions include:
- `ALLOW`
- `STEP_UP_AUTH`
- `MANUAL_REVIEW`
- `HOLD`
- `BLOCK`

Policy use guidance:
- REVIEW/HIGH outcomes should be reviewable and auditable.
- Final fraud confirmation should come from case resolution process, not score alone.

## 3. Reason Codes

Reason codes are implemented to improve operational interpretability, but they are:
- partly policy-derived
- partly heuristic (metadata and simple behavioral rules)
- not causal explanations

Therefore, reason codes are decision-support hints, not proof of fraud intent.

## 4. Fairness and Bias

Dataset limitation:
- No explicit protected attributes available in the baseline dataset.

Implication:
- Demographic fairness claims cannot be made directly from this dataset.

Recommended operational fairness checks:
- monitor false-positive rates across transaction amount/time/channel slices
- track outcome distributions by case status (`CONFIRMED_FRAUD`, `FALSE_POSITIVE`)

## 5. Privacy and Data Handling

Current design:
- model input contract is numeric features + optional transaction metadata
- internal endpoint with labels is token-protected

Recommended production controls (not fully implemented):
- strict PII minimization and redaction in logs
- encrypted storage and transport
- role-based access to case notes and investigation details

## 6. Safety and Harm Controls

Potential harms:
- false positives leading to customer friction
- false negatives leading to fraud loss

Mitigations implemented:
- explicit tiered policy with operational review path
- case lifecycle tracking and timeline for auditability
- monitoring of alert/case status metrics

## 7. Current Gaps and Honest Status

Implemented:
- score semantics transparency
- lifecycle tracking and timeline
- reason-code visibility

Not implemented yet:
- calibrated probabilities
- full auth/RBAC and tamper-resistant audit logs
- drift-triggered governance automation

## 8. Governance Recommendation

Before production rollout, require:
- policy owner sign-off on thresholds and action mapping
- analyst SOP for case transitions and escalation
- periodic review of false positives and confirmed fraud outcomes
- secure access controls for case operations APIs

## 9. Cross-Reference

For full implementation/proposed matrix and deployment honesty labels, see:
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`
