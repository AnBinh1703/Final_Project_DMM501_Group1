/* global window, ApiClient, DemoData, DashboardUI, DashboardUIUtil */

(function () {
  const DEFAULT_API = 'http://localhost:8000';
  const HEALTH_POLL_MS = 5000;
  const MAX_CHART_POINTS = 140;
  const MAX_FEED_ITEMS = 2500;
  const MAX_CASE_ITEMS = 1200;

  function classifyRisk(fraudProbability, threshold) {
    if (typeof fraudProbability !== 'number' || !Number.isFinite(fraudProbability)) return 'Normal';
    if (fraudProbability < 0.05) return 'Normal';
    if (typeof threshold === 'number' && Number.isFinite(threshold) && fraudProbability >= threshold) return 'Fraud';
    return 'Suspicious';
  }

  function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
      if (signal && signal.aborted) return reject(new Error('aborted'));
      const id = setTimeout(resolve, ms);
      if (!signal) return;
      signal.addEventListener('abort', () => {
        clearTimeout(id);
        reject(new Error('aborted'));
      }, { once: true });
    });
  }

  function normalizeBaseUrl(s) {
    const trimmed = String(s || '').trim();
    return trimmed ? trimmed.replace(/\/+$/, '') : DEFAULT_API;
  }

  function clampPage(page, totalPages) {
    const p = Math.max(1, Math.floor(page || 1));
    const t = Math.max(1, Math.floor(totalPages || 1));
    return Math.min(p, t);
  }

  function paginate(items, page, pageSize) {
    const size = Math.max(1, Math.floor(pageSize || 25));
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / size));
    const p = clampPage(page, totalPages);
    const start = (p - 1) * size;
    const end = Math.min(start + size, total);
    return { page: p, pageSize: size, total, totalPages, slice: items.slice(start, end) };
  }

  async function copyToClipboard(text) {
    const t = String(text || '');
    if (!t) return false;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(t);
        return true;
      }
    } catch (_) { /* ignore */ }

    // Fallback (best-effort): hidden textarea + execCommand
    try {
      const ta = document.createElement('textarea');
      ta.value = t;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return Boolean(ok);
    } catch (_) {
      return false;
    }
  }

  const state = {
    apiBaseUrl: DEFAULT_API,
    connected: false,
    modelLoaded: false,
    modelVersion: null,
    expectedFeatures: null,
    threshold: null,

    activeView: 'dashboard', // 'dashboard' | 'review'
    running: false,
    mode: 'real', // 'real' | 'random'
    intervalMs: 1000,

    // KPIs
    total: 0,
    fraud: 0,
    suspicious: 0,
    avgProbability: 0,
    lastLatencyMs: null,

    chartPoints: [],
    consecutiveErrors: 0,
    streamAbort: null,

    // Data stores (newest-first)
    nextId: 1,
    feedItems: [],
    caseItems: [],

    // Feed pagination
    feedPage: 1,
    feedPageSize: 25,
    feedSelectedId: null,

    // Review filters + pagination
    reviewRiskFilter: 'all', // all | Suspicious | Fraud
    reviewHandledFilter: 'unhandled', // unhandled | all | handled
    reviewSearch: '',
    reviewPage: 1,
    reviewPageSize: 10,
    reviewSelectedId: null,
  };

  const ui = new DashboardUI();
  let api = new ApiClient(DEFAULT_API);

  function els() {
    return {
      // Common controls
      apiBaseUrlInput: document.getElementById('apiBaseUrlInput'),
      applyApiBtn: document.getElementById('applyApiBtn'),
      modeSelect: document.getElementById('modeSelect'),
      speedSelect: document.getElementById('speedSelect'),
      startBtn: document.getElementById('startBtn'),
      stopBtn: document.getElementById('stopBtn'),
      resetBtn: document.getElementById('resetBtn'),

      // Tabs
      tabDashboard: document.getElementById('tabDashboard'),
      tabReview: document.getElementById('tabReview'),

      // Feed pager
      feedPrevBtn: document.getElementById('feedPrevBtn'),
      feedNextBtn: document.getElementById('feedNextBtn'),
      feedPageSize: document.getElementById('feedPageSize'),

      // Review controls
      reviewRiskFilter: document.getElementById('reviewRiskFilter'),
      reviewHandledFilter: document.getElementById('reviewHandledFilter'),
      reviewSearchInput: document.getElementById('reviewSearchInput'),
      reviewPrevBtn: document.getElementById('reviewPrevBtn'),
      reviewNextBtn: document.getElementById('reviewNextBtn'),
      reviewPageSize: document.getElementById('reviewPageSize'),

      // Case actions
      caseCopyPayloadBtn: document.getElementById('caseCopyPayloadBtn'),
      caseRescoreBtn: document.getElementById('caseRescoreBtn'),
      caseToggleHandledBtn: document.getElementById('caseToggleHandledBtn'),
      caseSaveNoteBtn: document.getElementById('caseSaveNoteBtn'),
    };
  }

  function setButtons() {
    const { startBtn, stopBtn } = els();
    const contractOk = state.expectedFeatures === 30;
    const canStart = state.connected && state.modelLoaded && contractOk;
    if (startBtn) startBtn.disabled = !canStart || state.running;
    if (stopBtn) stopBtn.disabled = !state.running;
  }

  function refreshHeader() {
    ui.setModelInfo({
      modelVersion: state.modelVersion || '-',
      threshold: state.threshold,
      expectedFeatures: state.expectedFeatures,
    });
  }

  function setBanner(text) {
    if (ui.el.statusBannerText) ui.el.statusBannerText.textContent = text || '-';
  }

  async function pollHealthOnce() {
    try {
      const body = await api.getHealth();
      state.connected = true;
      state.modelLoaded = Boolean(body.model_loaded);
      state.modelVersion = body.model_version ? String(body.model_version) : '-';
      state.expectedFeatures = (typeof body.expected_features === 'number') ? body.expected_features : null;

      const contractOk = state.expectedFeatures === 30;
      const msg = contractOk
        ? `ok • model_loaded=${state.modelLoaded} • expected_features=${state.expectedFeatures} • model_version=${state.modelVersion}`
        : `connected • expected_features=${state.expectedFeatures} (dashboard requires 30: Time,V1..V28,Amount)`;

      ui.setConnectionStatus({ connected: true, modelLoaded: state.modelLoaded, message: msg });
      refreshHeader();
      ui.clearError();
      setButtons();
      return body;
    } catch (err) {
      state.connected = false;
      state.modelLoaded = false;
      ui.setConnectionStatus({ connected: false, modelLoaded: false, message: 'backend unreachable — check API Base URL' });
      ui.showError(err && err.message ? err.message : String(err));
      setButtons();
      return null;
    }
  }

  function updateKPIs() {
    ui.updateKPIs({
      total: state.total,
      fraud: state.fraud,
      suspicious: state.suspicious,
      avgProbability: state.avgProbability,
      lastLatencyMs: state.lastLatencyMs,
    });
  }

  function pushChartPoint(probability) {
    state.chartPoints.push({ probability });
    if (state.chartPoints.length > MAX_CHART_POINTS) state.chartPoints.shift();
    ui.drawChart({ points: state.chartPoints, threshold: state.threshold });
  }

  function recomputeKPIsFromFeed() {
    // Recompute totals only from OK predictions (errors excluded)
    let total = 0;
    let fraud = 0;
    let suspicious = 0;
    let avg = 0;

    for (const item of state.feedItems) {
      if (item.status !== 'OK') continue;
      total += 1;
      avg += item.fraudProbability;
      if (item.riskLevel === 'Fraud') fraud += 1;
      if (item.riskLevel === 'Suspicious') suspicious += 1;
    }
    state.total = total;
    state.fraud = fraud;
    state.suspicious = suspicious;
    state.avgProbability = total ? (avg / total) : 0;
  }

  function renderFeed({ incremental } = {}) {
    const pageInfo = paginate(state.feedItems, state.feedPage, state.feedPageSize);
    state.feedPage = pageInfo.page;

    ui.setFeedPager({ page: pageInfo.page, totalPages: pageInfo.totalPages, totalItems: pageInfo.total });

    if (!incremental) {
      ui.renderFeedPage(pageInfo.slice, { selectedId: state.feedSelectedId });
    }

    const meta = (state.feedPage === 1)
      ? 'Newest items shown (live)'
      : `History page ${state.feedPage} (live stream continues; return to page 1 to follow)`;
    ui.setFeedMeta(meta);
  }

  function filterCases() {
    const risk = state.reviewRiskFilter;
    const handled = state.reviewHandledFilter;
    const q = String(state.reviewSearch || '').trim().toLowerCase();

    return state.caseItems.filter((c) => {
      if (risk !== 'all' && c.riskLevel !== risk) return false;
      if (handled === 'handled' && !c.handled) return false;
      if (handled === 'unhandled' && c.handled) return false;
      if (q && !String(c.requestId || '').toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function renderReview() {
    const filtered = filterCases();
    const pageInfo = paginate(filtered, state.reviewPage, state.reviewPageSize);
    state.reviewPage = pageInfo.page;

    ui.setReviewPager({ page: pageInfo.page, totalPages: pageInfo.totalPages, totalItems: pageInfo.total });
    ui.renderReviewCases(pageInfo.slice, { selectedId: state.reviewSelectedId });

    const selected = getCaseById(state.reviewSelectedId);
    ui.renderCaseDetails(selected);
  }

  function switchView(view) {
    state.activeView = view === 'review' ? 'review' : 'dashboard';
    ui.setActiveView(state.activeView);
    if (state.activeView === 'dashboard') renderFeed({ incremental: false });
    else renderReview();
  }

  function addFeedItem(item) {
    state.feedItems.unshift(item);
    if (state.feedItems.length > MAX_FEED_ITEMS) state.feedItems.pop();
  }

  function addCaseItem(item) {
    state.caseItems.unshift(item);
    if (state.caseItems.length > MAX_CASE_ITEMS) state.caseItems.pop();
  }

  function getCaseById(id) {
    if (id == null) return null;
    const s = String(id);
    return state.caseItems.find(c => String(c.id) === s) || null;
  }

  function openCase(id, { switchToReview } = {}) {
    state.feedSelectedId = id;
    state.reviewSelectedId = id;

    if (switchToReview) switchView('review');
    else if (state.activeView === 'dashboard') renderFeed({ incremental: false });
    else renderReview();
  }

  function recordPrediction({ result, tx, timestamp }) {
    state.lastLatencyMs = result._latencyMs;
    state.threshold = result.threshold;
    state.modelVersion = result.model_version || state.modelVersion;

    const p = result.fraud_probability;
    const risk = classifyRisk(p, state.threshold);

    const id = state.nextId++;
    const entry = {
      id,
      timestamp,
      requestId: result.request_id,
      amount: tx.amount,
      fraudProbability: p,
      fraudLabel: result.fraud_label,
      threshold: result.threshold,
      riskLevel: risk,
      latencyMs: result._latencyMs,
      status: 'OK',
      source: tx.source,
      features: tx.features,

      handled: false,
      note: '',
      noteSavedAt: null,
    };

    addFeedItem(entry);

    // Fast path: update dashboard feed without full re-render if on page 1.
    if (state.activeView === 'dashboard' && state.feedPage === 1) {
      ui.prependFeedRow(entry, { maxRows: state.feedPageSize, selectedId: state.feedSelectedId });
      ui.setFeedPager({
        page: 1,
        totalPages: Math.max(1, Math.ceil(state.feedItems.length / state.feedPageSize)),
        totalItems: state.feedItems.length,
      });
    } else if (state.activeView === 'dashboard') {
      // Keep counts updated; leave table as-is
      ui.setFeedPager({
        page: state.feedPage,
        totalPages: Math.max(1, Math.ceil(state.feedItems.length / state.feedPageSize)),
        totalItems: state.feedItems.length,
      });
    }

    if (risk !== 'Normal') {
      addCaseItem(entry);
      ui.prependAlert({
        id: entry.id,
        requestId: entry.requestId,
        fraudProbability: entry.fraudProbability,
        amount: entry.amount,
        riskLevel: entry.riskLevel,
        timestamp: entry.timestamp,
      });

      if (state.activeView === 'review') {
        // If user is reviewing, refresh the review list to include new incoming cases.
        renderReview();
      }
    }

    if (ui.el.chartLastThr) ui.el.chartLastThr.textContent = state.threshold.toFixed(4);
    pushChartPoint(p);

    // KPIs update
    recomputeKPIsFromFeed();
    updateKPIs();
    refreshHeader();
  }

  function recordError({ message, tx, timestamp, latencyMs }) {
    const id = state.nextId++;
    const entry = {
      id,
      timestamp,
      requestId: '-',
      amount: tx && typeof tx.amount === 'number' ? tx.amount : null,
      fraudProbability: null,
      fraudLabel: null,
      threshold: state.threshold != null ? state.threshold : 0,
      riskLevel: '-',
      latencyMs: (typeof latencyMs === 'number' && Number.isFinite(latencyMs)) ? latencyMs : null,
      status: 'ERROR',
      source: tx && tx.source ? tx.source : '-',
      features: tx && Array.isArray(tx.features) ? tx.features : null,
      handled: false,
      note: '',
      noteSavedAt: null,
    };
    addFeedItem(entry);

    if (state.activeView === 'dashboard' && state.feedPage === 1) {
      ui.prependFeedRow(entry, { maxRows: state.feedPageSize, selectedId: state.feedSelectedId });
    }
    ui.setFeedPager({
      page: state.feedPage === 1 ? 1 : state.feedPage,
      totalPages: Math.max(1, Math.ceil(state.feedItems.length / state.feedPageSize)),
      totalItems: state.feedItems.length,
    });

    ui.showError(message);
  }

  async function getNextTransaction() {
    if (state.mode === 'real') {
      if (typeof DemoData.ensureRealSamplesLoaded === 'function') await DemoData.ensureRealSamplesLoaded();
      return await DemoData.getNextRealTransaction();
    }
    return DemoData.generateRandomTransaction();
  }

  async function streamLoop(signal) {
    setBanner(`stream=running • mode=${state.mode} • every=${state.intervalMs}ms`);
    ui.setRunStateText(`stream=running • mode=${state.mode} • interval=${state.intervalMs}ms`);

    while (!signal.aborted && state.running) {
      const now = new Date();
      const timestamp = DashboardUIUtil.formatIsoTime(now);
      let tx = null;

      try {
        tx = await getNextTransaction();
        if (!tx || !Array.isArray(tx.features) || tx.features.length !== 30) {
          throw new Error('Transaction generator produced invalid features (expected 30).');
        }
        if (tx.features.some(v => typeof v !== 'number' || !Number.isFinite(v))) {
          throw new Error('Transaction generator produced non-finite numeric values.');
        }

        const result = await api.predictTransaction(tx.features);
        state.consecutiveErrors = 0;
        ui.clearError();
        recordPrediction({ result, tx, timestamp });
      } catch (err) {
        if (signal.aborted || !state.running) break;
        state.consecutiveErrors += 1;

        const message = err && err.message ? err.message : String(err);
        const latency = (err && typeof err._latencyMs === 'number') ? err._latencyMs : null;
        recordError({ message, tx, timestamp, latencyMs: latency });

        if (state.consecutiveErrors >= 4) {
          stopStream();
          setBanner('stream=stopped • too many consecutive errors');
          ui.setRunStateText('stream=stopped');
          break;
        }
      }

      try {
        await sleep(state.intervalMs, signal);
      } catch (_) {
        break;
      }
    }
  }

  function startStream() {
    if (state.running) return;
    if (!state.connected || !state.modelLoaded) {
      ui.showError('Cannot start stream: backend not ready (check connection/model_loaded).');
      return;
    }
    if (state.expectedFeatures !== 30) {
      ui.showError(`Cannot start stream: backend reports expected_features=${state.expectedFeatures} (requires 30).`);
      return;
    }

    state.running = true;
    state.consecutiveErrors = 0;
    ui.clearError();
    setButtons();

    const controller = new AbortController();
    state.streamAbort = controller;
    streamLoop(controller.signal).catch(() => {});
  }

  function stopStream() {
    state.running = false;
    if (state.streamAbort) {
      try { state.streamAbort.abort(); } catch (_) { /* ignore */ }
    }
    state.streamAbort = null;
    setButtons();
    setBanner('stream=stopped');
    ui.setRunStateText('stream=stopped');
  }

  function resetDashboard() {
    stopStream();
    state.total = 0;
    state.fraud = 0;
    state.suspicious = 0;
    state.avgProbability = 0;
    state.lastLatencyMs = null;
    state.chartPoints = [];
    state.consecutiveErrors = 0;

    state.feedItems = [];
    state.caseItems = [];
    state.nextId = 1;

    state.feedPage = 1;
    state.feedSelectedId = null;
    state.reviewPage = 1;
    state.reviewSelectedId = null;
    state.reviewRiskFilter = 'all';
    state.reviewHandledFilter = 'unhandled';
    state.reviewSearch = '';

    DemoData.reset();
    ui.resetPanels();
    // Reset visible control values (so filters match state).
    try {
      const e = els();
      if (e.reviewRiskFilter) e.reviewRiskFilter.value = 'all';
      if (e.reviewHandledFilter) e.reviewHandledFilter.value = 'unhandled';
      if (e.reviewSearchInput) e.reviewSearchInput.value = '';
    } catch (_) { /* ignore */ }

    updateKPIs();
    refreshHeader();
    ui.clearError();
    setBanner('reset complete');
    renderFeed({ incremental: false });
    renderReview();
    switchView('dashboard');
  }

  function applyApiBaseUrl() {
    const { apiBaseUrlInput } = els();
    const next = normalizeBaseUrl(apiBaseUrlInput ? apiBaseUrlInput.value : DEFAULT_API);
    state.apiBaseUrl = next;
    api.setBaseUrl(next);
    try { localStorage.setItem('fraud_api_url', next); } catch (_) { /* ignore */ }
    pollHealthOnce().catch(() => {});
  }

  function attachHandlers() {
    const e = els();

    // Tabs
    e.tabDashboard.addEventListener('click', () => switchView('dashboard'));
    e.tabReview.addEventListener('click', () => switchView('review'));

    // API base URL
    e.applyApiBtn.addEventListener('click', applyApiBaseUrl);
    e.apiBaseUrlInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') applyApiBaseUrl();
    });

    // Stream controls
    e.modeSelect.addEventListener('change', () => {
      state.mode = e.modeSelect.value === 'random' ? 'random' : 'real';
      setBanner(`mode=${state.mode}`);
    });
    e.speedSelect.addEventListener('change', () => {
      const ms = parseInt(e.speedSelect.value, 10);
      state.intervalMs = Number.isFinite(ms) ? ms : 1000;
      setBanner(`interval=${state.intervalMs}ms`);
    });
    e.startBtn.addEventListener('click', startStream);
    e.stopBtn.addEventListener('click', stopStream);
    e.resetBtn.addEventListener('click', resetDashboard);

    // Feed pager
    e.feedPrevBtn.addEventListener('click', () => {
      state.feedPage = Math.max(1, state.feedPage - 1);
      renderFeed({ incremental: false });
    });
    e.feedNextBtn.addEventListener('click', () => {
      state.feedPage = state.feedPage + 1;
      renderFeed({ incremental: false });
    });
    e.feedPageSize.addEventListener('change', () => {
      state.feedPageSize = parseInt(e.feedPageSize.value, 10) || 25;
      state.feedPage = 1;
      renderFeed({ incremental: false });
    });

    // Review filters
    e.reviewRiskFilter.addEventListener('change', () => {
      state.reviewRiskFilter = e.reviewRiskFilter.value || 'all';
      state.reviewPage = 1;
      renderReview();
    });
    e.reviewHandledFilter.addEventListener('change', () => {
      state.reviewHandledFilter = e.reviewHandledFilter.value || 'unhandled';
      state.reviewPage = 1;
      renderReview();
    });
    e.reviewSearchInput.addEventListener('input', () => {
      state.reviewSearch = e.reviewSearchInput.value || '';
      state.reviewPage = 1;
      renderReview();
    });

    // Review pager
    e.reviewPrevBtn.addEventListener('click', () => {
      state.reviewPage = Math.max(1, state.reviewPage - 1);
      renderReview();
    });
    e.reviewNextBtn.addEventListener('click', () => {
      state.reviewPage = state.reviewPage + 1;
      renderReview();
    });
    e.reviewPageSize.addEventListener('change', () => {
      state.reviewPageSize = parseInt(e.reviewPageSize.value, 10) || 10;
      state.reviewPage = 1;
      renderReview();
    });

    // Case actions
    e.caseCopyPayloadBtn.addEventListener('click', async () => {
      const c = getCaseById(state.reviewSelectedId);
      if (!c || !Array.isArray(c.features) || c.features.length !== 30) {
        ui.showError('No selected case with valid features.');
        return;
      }
      const payload = JSON.stringify({ features: c.features });
      const ok = await copyToClipboard(payload);
      if (ui.el.caseNoteSavedText) ui.el.caseNoteSavedText.textContent = ok ? 'copied payload' : 'copy failed';
    });

    e.caseRescoreBtn.addEventListener('click', async () => {
      const c = getCaseById(state.reviewSelectedId);
      if (!c || !Array.isArray(c.features) || c.features.length !== 30) {
        ui.showError('No selected case with valid features.');
        return;
      }
      if (!state.connected || !state.modelLoaded) {
        ui.showError('Backend not ready (check connection/model_loaded).');
        return;
      }
      const now = new Date();
      const timestamp = DashboardUIUtil.formatIsoTime(now);
      const tx = { source: 'manual', features: c.features, amount: c.amount };

      try {
        const result = await api.predictTransaction(c.features);
        recordPrediction({ result, tx, timestamp });
        if (ui.el.caseNoteSavedText) ui.el.caseNoteSavedText.textContent = 'rescored';
      } catch (err) {
        ui.showError(err && err.message ? err.message : String(err));
      }
    });

    e.caseToggleHandledBtn.addEventListener('click', () => {
      const c = getCaseById(state.reviewSelectedId);
      if (!c) return;
      c.handled = !c.handled;
      renderReview();
    });

    e.caseSaveNoteBtn.addEventListener('click', () => {
      const c = getCaseById(state.reviewSelectedId);
      if (!c) return;
      const note = ui.el.caseNoteInput ? String(ui.el.caseNoteInput.value || '') : '';
      c.note = note;
      c.noteSavedAt = DashboardUIUtil.formatIsoTime(new Date());
      renderReview();
    });
  }

  function initFromStorage() {
    let stored = null;
    try { stored = localStorage.getItem('fraud_api_url'); } catch (_) { /* ignore */ }
    state.apiBaseUrl = normalizeBaseUrl(stored || DEFAULT_API);
    api = new ApiClient(state.apiBaseUrl);
  }

  function boot() {
    ui.init();
    initFromStorage();

    const e = els();
    e.apiBaseUrlInput.value = state.apiBaseUrl;
    state.intervalMs = parseInt(e.speedSelect.value, 10) || 1000;
    state.mode = e.modeSelect.value === 'random' ? 'random' : 'real';

    state.feedPageSize = parseInt(e.feedPageSize.value, 10) || 25;
    state.reviewPageSize = parseInt(e.reviewPageSize.value, 10) || 10;

    attachHandlers();

    // Expose minimal controller for UI click hooks.
    window.FraudDashboard = {
      openCase,
      switchView,
    };

    ui.resetPanels();
    updateKPIs();
    ui.setRunStateText('stream=stopped');
    ui.setActiveView('dashboard');
    renderFeed({ incremental: false });
    renderReview();

    pollHealthOnce().catch(() => {});
    setInterval(() => pollHealthOnce().catch(() => {}), HEALTH_POLL_MS);
    setButtons();
    setBanner('ready');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
