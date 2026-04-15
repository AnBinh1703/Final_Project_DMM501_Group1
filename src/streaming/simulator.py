from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from src.data.samples import sample_dataset_rows
from src.features.random_features import generate_random_features


@dataclass
class StreamConfig:
    base_transactions_per_second: float = 1.2
    burst_transactions_per_second: float = 14.0
    burst_start_prob_per_pull: float = 0.06
    burst_min_events: int = 15
    burst_max_events: int = 80
    base_fraud_rate: float = 0.0017
    attack_fraud_rate: float = 0.01
    # Rare elevated-fraud windows (e.g., compromised merchant/bin). Keep this rare by default.
    attack_start_prob_per_pull: float = 0.0003
    attack_min_events: int = 20
    attack_max_events: int = 120


class StreamSimulator:
    """
    Stateful transaction stream generator.

    Properties:
    - Time-ordered events (simulated event_time_utc).
    - Bursty traffic (variable inter-arrival times).
    - Rare "attack windows" where fraud base-rate increases.

    Ground truth labels are never returned by this component.
    """

    def __init__(
        self,
        *,
        dataset_path: Path | None,
        feature_columns: list[str],
        seed: int = 42,
        config: StreamConfig | None = None,
    ) -> None:
        self._dataset_path = dataset_path if dataset_path and dataset_path.exists() else None
        self._feature_columns = list(feature_columns)
        self._rng = np.random.default_rng(seed)
        self._seed_counter = int(seed)
        self._cfg = config or StreamConfig()

        self._event_seq = 0
        self._now = datetime.now(UTC)
        self._burst_remaining = 0
        self._attack_remaining = 0

        try:
            self._time_idx = self._feature_columns.index("Time")
        except ValueError:
            self._time_idx = None
        try:
            self._amount_idx = self._feature_columns.index("Amount")
        except ValueError:
            self._amount_idx = None

    def _maybe_start_burst(self) -> None:
        if self._burst_remaining > 0:
            return
        if self._rng.random() < float(self._cfg.burst_start_prob_per_pull):
            span = max(1, int(self._cfg.burst_max_events - self._cfg.burst_min_events + 1))
            self._burst_remaining = int(self._cfg.burst_min_events + int(self._rng.integers(0, span)))

    def _maybe_start_attack(self) -> None:
        if self._attack_remaining > 0:
            return
        if self._rng.random() < float(self._cfg.attack_start_prob_per_pull):
            span = max(1, int(self._cfg.attack_max_events - self._cfg.attack_min_events + 1))
            self._attack_remaining = int(self._cfg.attack_min_events + int(self._rng.integers(0, span)))

    def _current_tps(self) -> float:
        return float(self._cfg.burst_transactions_per_second if self._burst_remaining > 0 else self._cfg.base_transactions_per_second)

    def _current_fraud_rate(self) -> float:
        return float(self._cfg.attack_fraud_rate if self._attack_remaining > 0 else self._cfg.base_fraud_rate)

    def _advance_time(self) -> None:
        tps = max(0.05, self._current_tps())
        dt_s = float(self._rng.exponential(1.0 / tps))
        self._now = self._now + timedelta(seconds=dt_s)

    def pull(self, *, pace_ms: int, max_events: int) -> list[dict]:
        pace_ms = int(pace_ms)
        if pace_ms < 50:
            pace_ms = 50
        if pace_ms > 60_000:
            pace_ms = 60_000
        max_events = int(max_events)
        if max_events < 1:
            max_events = 1
        if max_events > 500:
            max_events = 500

        self._maybe_start_burst()
        self._maybe_start_attack()

        end_time = self._now + timedelta(milliseconds=pace_ms)
        events: list[dict] = []

        while len(events) < max_events:
            self._advance_time()
            if self._now > end_time and events:
                break

            want_fraud = bool(self._rng.random() < self._current_fraud_rate())
            tx = self._sample_one(want_fraud=want_fraud)
            tx["event_id"] = str(self._event_seq)
            tx["event_time_utc"] = self._now.isoformat()
            events.append(tx)

            self._event_seq += 1
            if self._burst_remaining > 0:
                self._burst_remaining -= 1
            if self._attack_remaining > 0:
                self._attack_remaining -= 1

        return events

    def _sample_one(self, *, want_fraud: bool) -> dict:
        if self._dataset_path is None:
            g = generate_random_features(n_features=len(self._feature_columns), mode="creditcard", seed=self._seed_counter)
            self._seed_counter += 1
            return {
                "source": "synthetic",
                "features": [float(v) for v in g.features],
                "time_s": float(g.time_s) if g.time_s is not None else None,
                "amount": float(g.amount) if g.amount is not None else None,
            }

        strategy = "fraud" if want_fraud else "legit"
        rows = sample_dataset_rows(
            dataset_path=self._dataset_path,
            feature_columns=self._feature_columns,
            n=1,
            strategy=strategy,
            seed=self._seed_counter,
            include_label=False,
        )
        self._seed_counter += 1

        s = rows[0]
        feats = s["features"]
        payload = {"source": "dataset", "features": feats}
        payload["time_s"] = float(feats[self._time_idx]) if self._time_idx is not None and len(feats) > self._time_idx else None
        payload["amount"] = float(feats[self._amount_idx]) if self._amount_idx is not None and len(feats) > self._amount_idx else None
        return payload
