/* global window */

(function () {
  function formatIsoTime(d) {
    const pad2 = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
  }

  function shortId(id) {
    const s = String(id || '');
    if (s.length <= 14) return s;
    return `${s.slice(0, 8)}…${s.slice(-4)}`;
  }

  function pct(x) {
    if (typeof x !== 'number' || !Number.isFinite(x)) return '-';
    return `${(x * 100).toFixed(2)}%`;
  }

  function money(x) {
    if (typeof x !== 'number' || !Number.isFinite(x)) return '-';
    return `$${x.toFixed(2)}`;
  }

  function clamp01(x) {
    if (x < 0) return 0;
    if (x > 1) return 1;
    return x;
  }

  function riskToRowClass(risk) {
    if (risk === 'High') return 'row-fraud';
    if (risk === 'Review') return 'row-suspicious';
    if (risk === 'Low') return 'row-normal';
    return '';
  }

  function riskToBadgeClass(risk) {
    if (risk === 'High') return 'badge-fraud';
    if (risk === 'Review') return 'badge-suspicious';
    return 'badge-normal';
  }

  class DashboardUI {
    constructor() {
      this.el = {};
      this.chart = { canvas: null, ctx: null };
    }

    init() {
      const $ = (id) => document.getElementById(id);
      this.el.connectionPill = $('connectionPill');
      this.el.connectionDot = $('connectionDot');
      this.el.connectionText = $('connectionText');

      this.el.modelVersionText = $('modelVersionText');
      this.el.thresholdText = $('thresholdText');
      this.el.expectedFeaturesText = $('expectedFeaturesText');
      this.el.scoreSemanticsText = $('scoreSemanticsText');

      this.el.statusBannerText = $('statusBannerText');
      this.el.errorBanner = $('errorBanner');
      this.el.errorBannerText = $('errorBannerText');

      this.el.runStateText = $('runStateText');
      this.el.kpiTotal = $('kpiTotal');
      this.el.kpiHigh = $('kpiHigh');
      this.el.kpiReview = $('kpiReview');
      this.el.kpiAlertRate = $('kpiAlertRate');
      this.el.kpiAvgScore = $('kpiAvgScore');
      this.el.kpiLastLatency = $('kpiLastLatency');

      this.el.alertsList = $('alertsList');
      this.el.alertsEmpty = $('alertsEmpty');

      this.el.feedBody = $('feedBody');
      this.el.feedEmptyRow = $('feedEmptyRow');
      this.el.feedMetaText = $('feedMetaText');
      this.el.feedPageText = $('feedPageText');
      this.el.feedCountText = $('feedCountText');
      this.el.feedPrevBtn = $('feedPrevBtn');
      this.el.feedNextBtn = $('feedNextBtn');
      this.el.feedPageSize = $('feedPageSize');

      this.el.chartLastProb = $('chartLastProb');
      this.el.chartLastThr = $('chartLastThr');

      this.chart.canvas = $('probChart');
      if (this.chart.canvas && this.chart.canvas.getContext) {
        this.chart.ctx = this.chart.canvas.getContext('2d');
      }

      // Tabs + views
      this.el.tabDashboard = $('tabDashboard');
      this.el.tabReview = $('tabReview');
      this.el.dashboardView = $('dashboardView');
      this.el.reviewView = $('reviewView');

      // Review view
      this.el.reviewRiskFilter = $('reviewRiskFilter');
      this.el.reviewHandledFilter = $('reviewHandledFilter');
      this.el.reviewSearchInput = $('reviewSearchInput');
      this.el.reviewBody = $('reviewBody');
      this.el.reviewEmptyRow = $('reviewEmptyRow');
      this.el.reviewPrevBtn = $('reviewPrevBtn');
      this.el.reviewNextBtn = $('reviewNextBtn');
      this.el.reviewPageText = $('reviewPageText');
      this.el.reviewPageSize = $('reviewPageSize');
      this.el.reviewCountText = $('reviewCountText');

      // Case details
      this.el.caseCardEmpty = $('caseCardEmpty');
      this.el.caseCard = $('caseCard');
      this.el.caseRequestId = $('caseRequestId');
      this.el.caseTimestamp = $('caseTimestamp');
      this.el.caseRisk = $('caseRisk');
      this.el.caseProb = $('caseProb');
      this.el.caseThr = $('caseThr');
      this.el.caseAmount = $('caseAmount');
      this.el.caseCopyPayloadBtn = $('caseCopyPayloadBtn');
      this.el.caseRescoreBtn = $('caseRescoreBtn');
      this.el.caseToggleHandledBtn = $('caseToggleHandledBtn');
      this.el.caseNoteInput = $('caseNoteInput');
      this.el.caseSaveNoteBtn = $('caseSaveNoteBtn');
      this.el.caseNoteSavedText = $('caseNoteSavedText');
      this.el.caseFeatures = $('caseFeatures');
    }

    setConnectionStatus({ connected, modelLoaded, message }) {
      const dot = this.el.connectionDot;
      const text = this.el.connectionText;
      if (!dot || !text) return;

      if (!connected) {
        dot.className = 'dot dot-red';
        text.textContent = 'Disconnected';
      } else if (!modelLoaded) {
        dot.className = 'dot dot-red';
        text.textContent = 'Connected • model_loaded=false';
      } else {
        dot.className = 'dot dot-green';
        text.textContent = 'Connected • model_loaded=true';
      }

      if (this.el.statusBannerText) this.el.statusBannerText.textContent = message || '-';
    }

    setModelInfo({ modelVersion, thresholdReview, thresholdHigh, scoreSemantics, expectedFeatures }) {
      if (this.el.modelVersionText) this.el.modelVersionText.textContent = modelVersion || '-';
      if (this.el.thresholdText) {
        const r = (typeof thresholdReview === 'number') ? thresholdReview.toFixed(4) : '-';
        const h = (typeof thresholdHigh === 'number') ? thresholdHigh.toFixed(4) : '-';
        this.el.thresholdText.textContent = `${r} / ${h}`;
      }
      if (this.el.expectedFeaturesText) this.el.expectedFeaturesText.textContent = (typeof expectedFeatures === 'number') ? String(expectedFeatures) : '-';

      if (this.el.chartLastThr) {
        const r = (typeof thresholdReview === 'number') ? thresholdReview.toFixed(4) : '-';
        const h = (typeof thresholdHigh === 'number') ? thresholdHigh.toFixed(4) : '-';
        this.el.chartLastThr.textContent = `${r} / ${h}`;
      }

      if (this.el.scoreSemanticsText) this.el.scoreSemanticsText.textContent = scoreSemantics || '-';
    }

    showError(message) {
      if (!this.el.errorBanner || !this.el.errorBannerText) return;
      this.el.errorBanner.style.display = '';
      this.el.errorBannerText.textContent = message || 'Unknown error';
    }

    clearError() {
      if (!this.el.errorBanner || !this.el.errorBannerText) return;
      this.el.errorBanner.style.display = 'none';
      this.el.errorBannerText.textContent = '-';
    }

    setRunStateText(text) {
      if (this.el.runStateText) this.el.runStateText.textContent = text;
    }

    updateKPIs({ total, high, review, avgRiskScore, lastLatencyMs }) {
      if (this.el.kpiTotal) this.el.kpiTotal.textContent = String(total || 0);
      if (this.el.kpiHigh) this.el.kpiHigh.textContent = String(high || 0);
      if (this.el.kpiReview) this.el.kpiReview.textContent = String(review || 0);

      const alertRate = total > 0 ? ((high + review) / total) : 0;
      if (this.el.kpiAlertRate) this.el.kpiAlertRate.textContent = `${(alertRate * 100).toFixed(2)}%`;

      if (this.el.kpiAvgScore) this.el.kpiAvgScore.textContent = pct(avgRiskScore);
      if (this.el.kpiLastLatency) {
        this.el.kpiLastLatency.textContent = (typeof lastLatencyMs === 'number' && Number.isFinite(lastLatencyMs))
          ? `${lastLatencyMs.toFixed(0)} ms`
          : '- ms';
      }
    }

    setActiveView(view) {
      const v = view === 'review' ? 'review' : 'dashboard';
      if (this.el.dashboardView) this.el.dashboardView.style.display = v === 'dashboard' ? '' : 'none';
      if (this.el.reviewView) this.el.reviewView.style.display = v === 'review' ? '' : 'none';
      if (this.el.tabDashboard) this.el.tabDashboard.classList.toggle('tab-active', v === 'dashboard');
      if (this.el.tabReview) this.el.tabReview.classList.toggle('tab-active', v === 'review');
    }

    setFeedPager({ page, totalPages, totalItems }) {
      if (this.el.feedPageText) this.el.feedPageText.textContent = `${page} / ${totalPages}`;
      if (this.el.feedCountText) this.el.feedCountText.textContent = `${totalItems} items`;
      if (this.el.feedPrevBtn) this.el.feedPrevBtn.disabled = page <= 1;
      if (this.el.feedNextBtn) this.el.feedNextBtn.disabled = page >= totalPages;
    }

    setFeedMeta(text) {
      if (this.el.feedMetaText) this.el.feedMetaText.textContent = text || '';
    }

    setReviewPager({ page, totalPages, totalItems }) {
      if (this.el.reviewPageText) this.el.reviewPageText.textContent = `${page} / ${totalPages}`;
      if (this.el.reviewCountText) this.el.reviewCountText.textContent = `${totalItems} cases`;
      if (this.el.reviewPrevBtn) this.el.reviewPrevBtn.disabled = page <= 1;
      if (this.el.reviewNextBtn) this.el.reviewNextBtn.disabled = page >= totalPages;
    }

    _buildFeedRow(entry, { selectedId } = {}) {
      const tr = document.createElement('tr');
      tr.dataset.caseId = String(entry.id);
      if (String(entry.id) === String(selectedId)) tr.classList.add('selected');

      if (entry.status === 'ERROR') tr.classList.add('row-error');
      else tr.classList.add(riskToRowClass(entry.riskLevel));

      const td = (text, cls) => {
        const el = document.createElement('td');
        if (cls) el.className = cls;
        el.textContent = text;
        return el;
      };

      tr.appendChild(td(entry.timestamp, 'mono'));
      tr.appendChild(td(shortId(entry.requestId), 'mono'));
      tr.appendChild(td(money(entry.amount), 'right mono'));
      tr.appendChild(td(entry.status === 'OK' ? pct(entry.riskScore) : '-', 'right mono'));

      const riskTd = document.createElement('td');
      const riskBadge = document.createElement('span');
      riskBadge.className = `badge ${riskToBadgeClass(entry.riskLevel)}`;
      riskBadge.textContent = entry.riskLevel || '-';
      riskTd.appendChild(riskBadge);
      tr.appendChild(riskTd);

      tr.appendChild(td(entry.status === 'OK' ? String(entry.riskTier) : '-', 'center mono'));
      tr.appendChild(td(entry.status === 'OK' ? String(entry.action || '-') : '-', 'center mono'));
      const thrTxt = (entry.status === 'OK')
        ? `${Number(entry.thresholdReview).toFixed(4)} / ${Number(entry.thresholdHigh).toFixed(4)}`
        : '-';
      tr.appendChild(td(thrTxt, 'right mono'));
      tr.appendChild(td(entry.latencyMs != null ? `${entry.latencyMs.toFixed(0)} ms` : '-', 'right mono'));
      tr.appendChild(td(entry.status, entry.status === 'OK' ? 'muted' : ''));
      tr.appendChild(td(entry.source || '-', 'muted'));

      const isCase = entry.status === 'OK' && (entry.riskTier === 'REVIEW' || entry.riskTier === 'HIGH');
      if (isCase) {
        tr.classList.add('selectable');
        tr.addEventListener('click', () => {
          if (window.FraudDashboard && typeof window.FraudDashboard.openCase === 'function') {
            window.FraudDashboard.openCase(entry.id, { switchToReview: true });
          }
        });
      }

      return tr;
    }

    renderFeedPage(entries, { selectedId } = {}) {
      const tbody = this.el.feedBody;
      if (!tbody) return;

      while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

      if (!entries || entries.length === 0) {
        const tr = document.createElement('tr');
        tr.id = 'feedEmptyRow';
        const td = document.createElement('td');
        td.colSpan = 11;
        td.className = 'muted center';
        td.textContent = 'No items on this page.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        this.el.feedEmptyRow = tr;
        return;
      }

      for (const e of entries) {
        tbody.appendChild(this._buildFeedRow(e, { selectedId }));
      }
    }

    prependFeedRow(entry, { maxRows = 25, selectedId } = {}) {
      const tbody = this.el.feedBody;
      if (!tbody) return;

      if (this.el.feedEmptyRow) {
        try { this.el.feedEmptyRow.remove(); } catch (_) { /* ignore */ }
        this.el.feedEmptyRow = null;
      }

      const tr = this._buildFeedRow(entry, { selectedId });
      tbody.insertBefore(tr, tbody.firstChild);

      while (tbody.children.length > maxRows) {
        tbody.removeChild(tbody.lastElementChild);
      }
    }

    prependAlert(alert, { maxAlerts = 12 } = {}) {
      const container = this.el.alertsList;
      if (!container) return;

      if (this.el.alertsEmpty) this.el.alertsEmpty.style.display = 'none';

      const el = document.createElement('div');
      el.className = 'alert';
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        if (window.FraudDashboard && typeof window.FraudDashboard.openCase === 'function') {
          window.FraudDashboard.openCase(alert.id, { switchToReview: true });
        }
      });

      const id = document.createElement('div');
      id.className = 'id';
      id.textContent = alert.requestId;

      const ts = document.createElement('div');
      ts.className = 'ts';
      ts.textContent = alert.timestamp;

      const prob = document.createElement('div');
      prob.className = 'mono right';
      prob.textContent = pct(alert.riskScore);

      const risk = document.createElement('div');
      const badge = document.createElement('span');
      badge.className = `badge ${riskToBadgeClass(alert.riskLevel)}`;
      badge.textContent = `${alert.riskLevel} • ${money(alert.amount)}`;
      risk.appendChild(badge);

      el.appendChild(id);
      el.appendChild(ts);
      el.appendChild(prob);
      el.appendChild(risk);

      container.insertBefore(el, container.firstChild);

      while (container.children.length > maxAlerts + 1) {
        // +1 because the empty placeholder remains in DOM (hidden)
        container.removeChild(container.lastElementChild);
      }
    }

    resetPanels() {
      // Feed: remove all rows and re-add placeholder row.
      if (this.el.feedBody) {
        while (this.el.feedBody.firstChild) this.el.feedBody.removeChild(this.el.feedBody.firstChild);
        const tr = document.createElement('tr');
        tr.id = 'feedEmptyRow';
        const td = document.createElement('td');
        td.colSpan = 11;
        td.className = 'muted center';
        td.textContent = 'Stream not started.';
        tr.appendChild(td);
        this.el.feedBody.appendChild(tr);
        this.el.feedEmptyRow = tr;
      }

      // Alerts: remove all alerts (keep placeholder).
      if (this.el.alertsList) {
        const children = Array.from(this.el.alertsList.children);
        for (const c of children) {
          if (c && c.id === 'alertsEmpty') continue;
          if (c === this.el.alertsEmpty) continue;
          this.el.alertsList.removeChild(c);
        }
      }
      if (this.el.alertsEmpty) {
        this.el.alertsEmpty.style.display = '';
        this.el.alertsEmpty.textContent = 'No alerts yet.';
      }

      this.drawChart({ points: [], thresholdReview: null, thresholdHigh: null });
      if (this.el.chartLastProb) this.el.chartLastProb.textContent = '-';
      if (this.el.chartLastThr) this.el.chartLastThr.textContent = '-';

      // Review list
      if (this.el.reviewBody) {
        while (this.el.reviewBody.firstChild) this.el.reviewBody.removeChild(this.el.reviewBody.firstChild);
        const tr = document.createElement('tr');
        tr.id = 'reviewEmptyRow';
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'muted center';
        td.textContent = 'No cases yet.';
        tr.appendChild(td);
        this.el.reviewBody.appendChild(tr);
        this.el.reviewEmptyRow = tr;
      }

      this.renderCaseDetails(null);
    }

    renderReviewCases(cases, { selectedId } = {}) {
      const tbody = this.el.reviewBody;
      if (!tbody) return;

      while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

      if (!cases || cases.length === 0) {
        const tr = document.createElement('tr');
        tr.id = 'reviewEmptyRow';
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'muted center';
        td.textContent = 'No cases match the current filters.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        this.el.reviewEmptyRow = tr;
        return;
      }

      const td = (text, cls) => {
        const el = document.createElement('td');
        if (cls) el.className = cls;
        el.textContent = text;
        return el;
      };

      for (const c of cases) {
        const tr = document.createElement('tr');
        tr.classList.add('selectable');
        tr.dataset.caseId = String(c.id);
        if (String(c.id) === String(selectedId)) tr.classList.add('selected');

        tr.appendChild(td(c.timestamp, 'mono'));
        tr.appendChild(td(shortId(c.requestId), 'mono'));
        tr.appendChild(td(money(c.amount), 'right mono'));
        tr.appendChild(td(pct(c.riskScore), 'right mono'));

        const riskTd = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `badge ${riskToBadgeClass(c.riskLevel)}`;
        badge.textContent = c.riskLevel;
        riskTd.appendChild(badge);
        tr.appendChild(riskTd);

        tr.appendChild(td(c.handled ? 'yes' : 'no', c.handled ? 'muted' : ''));

        tr.addEventListener('click', () => {
          if (window.FraudDashboard && typeof window.FraudDashboard.openCase === 'function') {
            window.FraudDashboard.openCase(c.id, { switchToReview: false });
          }
        });

        tbody.appendChild(tr);
      }
    }

    renderCaseDetails(caseObj) {
      const has = Boolean(caseObj);
      if (this.el.caseCardEmpty) this.el.caseCardEmpty.style.display = has ? 'none' : '';
      if (this.el.caseCard) this.el.caseCard.style.display = has ? '' : 'none';
      if (!has) return;

      this.el.caseRequestId.textContent = caseObj.requestId;
      this.el.caseTimestamp.textContent = caseObj.timestamp;

      const badge = document.createElement('span');
      badge.className = `badge ${riskToBadgeClass(caseObj.riskLevel)}`;
      badge.textContent = caseObj.riskLevel;
      this.el.caseRisk.innerHTML = '';
      this.el.caseRisk.appendChild(badge);

      this.el.caseProb.textContent = pct(caseObj.riskScore);
      this.el.caseThr.textContent = (typeof caseObj.thresholdReview === 'number' && typeof caseObj.thresholdHigh === 'number')
        ? `${caseObj.thresholdReview.toFixed(4)} / ${caseObj.thresholdHigh.toFixed(4)}`
        : '-';
      this.el.caseAmount.textContent = money(caseObj.amount);

      this.el.caseNoteInput.value = caseObj.note || '';
      this.el.caseNoteSavedText.textContent = caseObj.noteSavedAt ? `saved ${caseObj.noteSavedAt}` : '';

      this.el.caseToggleHandledBtn.textContent = caseObj.handled ? 'Mark Unhandled' : 'Mark Handled';
      this.el.caseToggleHandledBtn.className = caseObj.handled ? 'btn btn-secondary' : 'btn btn-primary';

      // Features
      const feats = Array.isArray(caseObj.features) ? caseObj.features : [];
      this.el.caseFeatures.textContent = JSON.stringify(feats);
    }

    drawChart({ points, thresholdReview, thresholdHigh }) {
      const ctx = this.chart.ctx;
      const canvas = this.chart.canvas;
      if (!ctx || !canvas) return;

      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // Frame
      ctx.strokeStyle = 'rgba(148,163,184,0.22)';
      ctx.lineWidth = 1;
      ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

      const padding = 18;
      const plotW = width - padding * 2;
      const plotH = height - padding * 2;

      // Grid
      ctx.strokeStyle = 'rgba(148,163,184,0.10)';
      ctx.lineWidth = 1;
      for (let i = 1; i <= 4; i++) {
        const y = padding + (plotH * i) / 5;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
      }

      // Threshold lines (review + high)
      if (typeof thresholdReview === 'number' && Number.isFinite(thresholdReview)) {
        const yThr = padding + (1 - clamp01(thresholdReview)) * plotH;
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = 'rgba(245,158,11,0.85)';
        ctx.beginPath();
        ctx.moveTo(padding, yThr);
        ctx.lineTo(width - padding, yThr);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      if (typeof thresholdHigh === 'number' && Number.isFinite(thresholdHigh)) {
        const yThr = padding + (1 - clamp01(thresholdHigh)) * plotH;
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = 'rgba(239,68,68,0.90)';
        ctx.beginPath();
        ctx.moveTo(padding, yThr);
        ctx.lineTo(width - padding, yThr);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      if (!Array.isArray(points) || points.length < 2) return;
      const values = points.map(p => p.riskScore).filter(v => typeof v === 'number' && Number.isFinite(v));
      if (values.length < 2) return;

      ctx.strokeStyle = 'rgba(96,165,250,0.95)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < values.length; i++) {
        const x = padding + (i / (values.length - 1)) * plotW;
        const y = padding + (1 - clamp01(values[i])) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Last point
      const last = values[values.length - 1];
      const lx = padding + plotW;
      const ly = padding + (1 - clamp01(last)) * plotH;
      ctx.fillStyle = 'rgba(226,232,240,0.95)';
      ctx.beginPath();
      ctx.arc(lx, ly, 3, 0, Math.PI * 2);
      ctx.fill();

      if (this.el.chartLastProb) this.el.chartLastProb.textContent = pct(last);
    }
  }

  window.DashboardUI = DashboardUI;
  window.DashboardUIUtil = { formatIsoTime };
})();
