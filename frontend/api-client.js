/* global window */

(function () {
  function normalizeBaseUrl(s) {
    const trimmed = String(s || '').trim();
    if (!trimmed) return 'http://localhost:8000';
    return trimmed.replace(/\/+$/, '');
  }

  function withTimeout(ms, controller) {
    const id = setTimeout(() => {
      try { controller.abort(); } catch (_) { /* ignore */ }
    }, ms);
    return () => clearTimeout(id);
  }

  function safeJsonParse(text) {
    try { return JSON.parse(text); } catch (_) { return null; }
  }

  function assertHealthShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid /health response: not an object.');
    if (typeof body.status !== 'string') throw new Error('Invalid /health response: missing status.');
    if (typeof body.model_loaded !== 'boolean') throw new Error('Invalid /health response: missing model_loaded.');
    if (!('model_version' in body)) throw new Error('Invalid /health response: missing model_version.');
    if (!('expected_features' in body)) throw new Error('Invalid /health response: missing expected_features.');
    return body;
  }

  function assertPredictShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid /predict response: not an object.');
    if (typeof body.request_id !== 'string') throw new Error('Invalid /predict response: missing request_id.');
    if (typeof body.fraud_probability !== 'number') throw new Error('Invalid /predict response: missing fraud_probability.');
    if (body.fraud_label !== 0 && body.fraud_label !== 1) throw new Error('Invalid /predict response: missing fraud_label.');
    if (typeof body.threshold !== 'number') throw new Error('Invalid /predict response: missing threshold.');
    if (typeof body.model_version !== 'string') throw new Error('Invalid /predict response: missing model_version.');
    return body;
  }

  class ApiClient {
    constructor(baseUrl) {
      this.baseUrl = normalizeBaseUrl(baseUrl);
      this.defaultTimeoutMs = 3500;
    }

    setBaseUrl(next) {
      this.baseUrl = normalizeBaseUrl(next);
    }

    async getHealth() {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/health`;

      try {
        const resp = await fetch(url, { method: 'GET', signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);

        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Health check failed: ${detail}`);
        }

        return assertHealthShape(body);
      } finally {
        clear();
      }
    }

    async predictTransaction(features) {
      if (!Array.isArray(features)) throw new Error('predictTransaction: features must be an array.');
      if (features.length !== 30) throw new Error(`predictTransaction: expected 30 features, got ${features.length}.`);
      if (features.some(v => typeof v !== 'number' || !Number.isFinite(v))) {
        throw new Error('predictTransaction: all features must be finite numbers.');
      }

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/predict`;
      const payload = JSON.stringify({ features });
      const start = performance.now();

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          signal: controller.signal,
        });

        const text = await resp.text();
        const body = safeJsonParse(text);
        const latencyMs = performance.now() - start;

        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          const err = new Error(`Predict failed: ${detail}`);
          err._httpStatus = resp.status;
          err._latencyMs = latencyMs;
          throw err;
        }

        const parsed = assertPredictShape(body);
        return { ...parsed, _latencyMs: latencyMs };
      } finally {
        clear();
      }
    }
  }

  window.ApiClient = ApiClient;
})();

