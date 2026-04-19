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
    if (typeof body.risk_score !== 'number') throw new Error('Invalid /predict response: missing risk_score.');
    if (typeof body.risk_tier !== 'string') throw new Error('Invalid /predict response: missing risk_tier.');
    if (typeof body.action !== 'string') throw new Error('Invalid /predict response: missing action.');
    if (typeof body.decision_label !== 'string') throw new Error('Invalid /predict response: missing decision_label.');
    if (typeof body.decision_recommendation !== 'string') throw new Error('Invalid /predict response: missing decision_recommendation.');
    if (typeof body.decision_explanation !== 'string') throw new Error('Invalid /predict response: missing decision_explanation.');
    if (!Array.isArray(body.reason_codes)) throw new Error('Invalid /predict response: missing reason_codes.');
    if (typeof body.reason_summary !== 'string') throw new Error('Invalid /predict response: missing reason_summary.');
    if (typeof body.threshold_review !== 'number') throw new Error('Invalid /predict response: missing threshold_review.');
    if (typeof body.threshold_high !== 'number') throw new Error('Invalid /predict response: missing threshold_high.');
    if (typeof body.score_semantics !== 'string') throw new Error('Invalid /predict response: missing score_semantics.');
    if (typeof body.model_version !== 'string') throw new Error('Invalid /predict response: missing model_version.');
    return body;
  }

  function assertStreamPullShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid /stream/pull response: not an object.');
    if (typeof body.model_version !== 'string') throw new Error('Invalid /stream/pull response: missing model_version.');
    if (typeof body.score_semantics !== 'string') throw new Error('Invalid /stream/pull response: missing score_semantics.');
    if (typeof body.threshold_review !== 'number') throw new Error('Invalid /stream/pull response: missing threshold_review.');
    if (typeof body.threshold_high !== 'number') throw new Error('Invalid /stream/pull response: missing threshold_high.');
    if (!Array.isArray(body.events) || body.events.length < 1) throw new Error('Invalid /stream/pull response: missing events.');
    const e = body.events[0];
    if (!e || typeof e !== 'object') throw new Error('Invalid /stream/pull response: event is not an object.');
    if (typeof e.event_id !== 'string') throw new Error('Invalid /stream/pull response: missing event_id.');
    if (typeof e.event_time_utc !== 'string') throw new Error('Invalid /stream/pull response: missing event_time_utc.');
    if (!Array.isArray(e.features) || e.features.length !== 30) throw new Error('Invalid /stream/pull response: invalid features.');
    if (typeof e.risk_score !== 'number') throw new Error('Invalid /stream/pull response: missing risk_score.');
    if (typeof e.risk_tier !== 'string') throw new Error('Invalid /stream/pull response: missing risk_tier.');
    if (typeof e.action !== 'string') throw new Error('Invalid /stream/pull response: missing action.');
    if (typeof e.decision_label !== 'string') throw new Error('Invalid /stream/pull response: missing decision_label.');
    if (typeof e.decision_recommendation !== 'string') throw new Error('Invalid /stream/pull response: missing decision_recommendation.');
    if (!Array.isArray(e.reason_codes)) throw new Error('Invalid /stream/pull response: missing reason_codes.');
    return body;
  }

  function assertAlertListShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid /alerts response: not an object.');
    if (typeof body.total !== 'number') throw new Error('Invalid /alerts response: missing total.');
    if (!Array.isArray(body.alerts)) throw new Error('Invalid /alerts response: missing alerts array.');
    return body;
  }

  function assertCaseListShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid /cases response: not an object.');
    if (typeof body.total !== 'number') throw new Error('Invalid /cases response: missing total.');
    if (!Array.isArray(body.cases)) throw new Error('Invalid /cases response: missing cases array.');
    return body;
  }

  function assertCaseShape(body) {
    if (!body || typeof body !== 'object') throw new Error('Invalid case response: not an object.');
    if (typeof body.case_id !== 'string') throw new Error('Invalid case response: missing case_id.');
    if (typeof body.case_status !== 'string') throw new Error('Invalid case response: missing case_status.');
    return body;
  }

  class ApiClient {
    constructor(baseUrl) {
      this.baseUrl = normalizeBaseUrl(baseUrl);
      this.defaultTimeoutMs = 3500;
      this.apiKey = '';
      this.actor = 'frontend-ui';
    }

    setBaseUrl(next) {
      this.baseUrl = normalizeBaseUrl(next);
    }

    setAuth({ apiKey = '', actor = 'frontend-ui' } = {}) {
      this.apiKey = String(apiKey || '').trim();
      this.actor = String(actor || '').trim() || 'frontend-ui';
    }

    _buildHeaders(extra = {}) {
      const headers = { ...extra };
      if (this.apiKey) headers.Authorization = `Bearer ${this.apiKey}`;
      if (this.actor) headers['X-Actor'] = this.actor;
      return headers;
    }

    async getHealth() {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/health`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
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
          headers: this._buildHeaders({ 'Content-Type': 'application/json' }),
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

    async getDatasetSamples({ n = 1, strategy = 'production', seed = 42 } = {}) {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/dataset/samples?n=${encodeURIComponent(String(n))}&strategy=${encodeURIComponent(String(strategy))}&seed=${encodeURIComponent(String(seed))}`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Dataset samples failed: ${detail}`);
        }
        if (!body || typeof body !== 'object' || !Array.isArray(body.samples)) {
          throw new Error('Invalid /dataset/samples response shape.');
        }
        return body;
      } finally {
        clear();
      }
    }

    async pullStream({ paceMs = 1000, maxEvents = 75 } = {}) {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/stream/pull?pace_ms=${encodeURIComponent(String(paceMs))}&max_events=${encodeURIComponent(String(maxEvents))}`;
      const start = performance.now();

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        const latencyMs = performance.now() - start;
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          const err = new Error(`Stream pull failed: ${detail}`);
          err._httpStatus = resp.status;
          err._latencyMs = latencyMs;
          throw err;
        }
        const parsed = assertStreamPullShape(body);
        return { ...parsed, _latencyMs: latencyMs };
      } finally {
        clear();
      }
    }

    async listAlerts({ status = null, limit = 100 } = {}) {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const statusQuery = status ? `&status=${encodeURIComponent(String(status))}` : '';
      const url = `${this.baseUrl}/alerts?limit=${encodeURIComponent(String(limit))}${statusQuery}`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`List alerts failed: ${detail}`);
        }
        return assertAlertListShape(body);
      } finally {
        clear();
      }
    }

    async getAlert(alertId) {
      if (!alertId) throw new Error('getAlert: alertId is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/alerts/${encodeURIComponent(String(alertId))}`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Get alert failed: ${detail}`);
        }
        return body;
      } finally {
        clear();
      }
    }

    async updateAlertStatus(alertId, { caseStatus, analystNote = '', actor = 'frontend-ui' } = {}) {
      if (!alertId) throw new Error('updateAlertStatus: alertId is required.');
      if (!caseStatus) throw new Error('updateAlertStatus: caseStatus is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/alerts/${encodeURIComponent(String(alertId))}/status`;

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: this._buildHeaders({ 'Content-Type': 'application/json' }),
          signal: controller.signal,
          body: JSON.stringify({ case_status: caseStatus, analyst_note: analystNote, actor }),
        });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Update alert status failed: ${detail}`);
        }
        return assertCaseShape(body);
      } finally {
        clear();
      }
    }

    async listCases({ status = null, limit = 200 } = {}) {
      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const statusQuery = status ? `&status=${encodeURIComponent(String(status))}` : '';
      const url = `${this.baseUrl}/cases?limit=${encodeURIComponent(String(limit))}${statusQuery}`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`List cases failed: ${detail}`);
        }
        return assertCaseListShape(body);
      } finally {
        clear();
      }
    }

    async getCase(caseId) {
      if (!caseId) throw new Error('getCase: caseId is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/cases/${encodeURIComponent(String(caseId))}`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Get case failed: ${detail}`);
        }
        return assertCaseShape(body);
      } finally {
        clear();
      }
    }

    async updateCaseStatus(caseId, { caseStatus, analystNote = '', actor = 'frontend-ui' } = {}) {
      if (!caseId) throw new Error('updateCaseStatus: caseId is required.');
      if (!caseStatus) throw new Error('updateCaseStatus: caseStatus is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/cases/${encodeURIComponent(String(caseId))}/status`;

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: this._buildHeaders({ 'Content-Type': 'application/json' }),
          signal: controller.signal,
          body: JSON.stringify({ case_status: caseStatus, analyst_note: analystNote, actor }),
        });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Update case status failed: ${detail}`);
        }
        return assertCaseShape(body);
      } finally {
        clear();
      }
    }

    async resolveCase(caseId, { resolution, analystNote = '', actor = 'frontend-ui' } = {}) {
      if (!caseId) throw new Error('resolveCase: caseId is required.');
      if (!resolution) throw new Error('resolveCase: resolution is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/cases/${encodeURIComponent(String(caseId))}/resolve`;

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: this._buildHeaders({ 'Content-Type': 'application/json' }),
          signal: controller.signal,
          body: JSON.stringify({ resolution, analyst_note: analystNote, actor }),
        });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Resolve case failed: ${detail}`);
        }
        return assertCaseShape(body);
      } finally {
        clear();
      }
    }

    async getCaseTimeline(caseId) {
      if (!caseId) throw new Error('getCaseTimeline: caseId is required.');

      const controller = new AbortController();
      const clear = withTimeout(this.defaultTimeoutMs, controller);
      const url = `${this.baseUrl}/cases/${encodeURIComponent(String(caseId))}/timeline`;

      try {
        const resp = await fetch(url, { method: 'GET', headers: this._buildHeaders(), signal: controller.signal });
        const text = await resp.text();
        const body = safeJsonParse(text);
        if (!resp.ok) {
          const detail = body && body.detail ? String(body.detail) : `HTTP ${resp.status}`;
          throw new Error(`Get case timeline failed: ${detail}`);
        }
        if (!body || typeof body !== 'object' || !Array.isArray(body.timeline)) {
          throw new Error('Invalid /cases/{id}/timeline response shape.');
        }
        return body;
      } finally {
        clear();
      }
    }
  }

  window.ApiClient = ApiClient;
})();
