// Streaming Demo Mode - JavaScript Implementation
// Real-Time Fraud Detection Transaction Stream

// ====================================================================
// DEMO STATE MANAGEMENT
// ====================================================================

const DemoState = {
  status: 'idle', // 'idle' | 'streaming' | 'paused' | 'error'
  isRunning: false,
  isPaused: false,
  mode: 'dataset', // 'dataset' or 'random'
  speedMultiplier: 1,
  baseDelayMs: 200,
  consecutiveErrors: 0,
  
  // Counters
  totalPredictions: 0,
  fraudCount: 0,
  legitimateCount: 0,
  latencies: [],
  probabilities: [],
  
  // Feed
  feedItems: [],
  maxFeedItems: 100,

  // Derived state
  lastThreshold: null,
  lastProbability: null,
  lastModelVersion: null,

  // In-flight controls
  currentAbortController: null,
  
  // UI Element References
  startDatasetBtn: null,
  startRandomBtn: null,
  pauseBtn: null,
  stopBtn: null,
  resetBtn: null,
  speedButtons: null,
  totalCountEl: null,
  fraudCountEl: null,
  legitCountEl: null,
  fraudRateEl: null,
  avgLatencyEl: null,
  avgProbEl: null,
  feedContainer: null,
  statusEl: null,
  modeEl: null,
  modelVersionEl: null,
  errorBannerEl: null,
  errorTextEl: null,
  chartCanvas: null,
  chartCtx: null,
  lastThrEl: null,
  lastProbEl: null,
};

// ====================================================================
// INITIALIZATION
// ====================================================================

function initializeStreamingDemo() {
  // Get DOM references
  DemoState.startDatasetBtn = document.getElementById('startDatasetStreamBtn');
  DemoState.startRandomBtn = document.getElementById('startRandomStreamBtn');
  DemoState.pauseBtn = document.getElementById('pauseStreamBtn');
  DemoState.stopBtn = document.getElementById('stopStreamBtn');
  DemoState.resetBtn = document.getElementById('resetStreamBtn');
  
  DemoState.totalCountEl = document.getElementById('demoTotalCount');
  DemoState.fraudCountEl = document.getElementById('demoFraudCount');
  DemoState.legitCountEl = document.getElementById('demoLegitCount');
  DemoState.fraudRateEl = document.getElementById('demoFraudRate');
  DemoState.avgLatencyEl = document.getElementById('demoAvgLatency');
  DemoState.avgProbEl = document.getElementById('demoAvgProb');
  DemoState.feedContainer = document.getElementById('demoLiveFeed');
  DemoState.statusEl = document.getElementById('demoStreamStatus');
  DemoState.modeEl = document.getElementById('demoStreamMode');
  DemoState.modelVersionEl = document.getElementById('demoModelVersion');
  DemoState.errorBannerEl = document.getElementById('demoErrorBanner');
  DemoState.errorTextEl = document.getElementById('demoErrorText');
  DemoState.chartCanvas = document.getElementById('demoProbChart');
  DemoState.lastThrEl = document.getElementById('demoLastThreshold');
  DemoState.lastProbEl = document.getElementById('demoLastProb');

  if (DemoState.chartCanvas && DemoState.chartCanvas.getContext) {
    DemoState.chartCtx = DemoState.chartCanvas.getContext('2d');
  }
  
  // Attach event listeners
  if (DemoState.startDatasetBtn) {
    DemoState.startDatasetBtn.addEventListener('click', startDatasetStream);
  }
  if (DemoState.startRandomBtn) {
    DemoState.startRandomBtn.addEventListener('click', startRandomStream);
  }
  if (DemoState.pauseBtn) {
    DemoState.pauseBtn.addEventListener('click', togglePauseStream);
  }
  if (DemoState.stopBtn) {
    DemoState.stopBtn.addEventListener('click', stopStream);
  }
  if (DemoState.resetBtn) {
    DemoState.resetBtn.addEventListener('click', resetDemoState);
  }
  
  // Speed control buttons
  document.querySelectorAll('[data-stream-speed]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const speed = parseInt(e.target.dataset.streamSpeed);
      setStreamSpeed(speed);
    });
  });
  
  updateStreamButtonStates();
  updateStatusUI();
  updateDemoDisplay();
}

// ====================================================================
// STREAM CONTROL FUNCTIONS
// ====================================================================

function startDatasetStream() {
  if (DemoState.isRunning) return;
  DemoState.mode = 'dataset';
  DemoState.isRunning = true;
  DemoState.isPaused = false;
  DemoState.status = 'streaming';
  DemoState.consecutiveErrors = 0;
  updateStreamButtonStates();
  updateStatusUI();
  runPredictionStream();
}

function startRandomStream() {
  if (DemoState.isRunning) return;
  DemoState.mode = 'random';
  DemoState.isRunning = true;
  DemoState.isPaused = false;
  DemoState.status = 'streaming';
  DemoState.consecutiveErrors = 0;
  updateStreamButtonStates();
  updateStatusUI();
  runPredictionStream();
}

function togglePauseStream() {
  if (DemoState.isRunning) {
    DemoState.isPaused = !DemoState.isPaused;
    DemoState.status = DemoState.isPaused ? 'paused' : 'streaming';
    updateStreamButtonStates();
    updateStatusUI();
  }
}

function stopStream() {
  DemoState.isRunning = false;
  DemoState.isPaused = false;
  DemoState.status = 'idle';
  if (DemoState.currentAbortController) {
    try { DemoState.currentAbortController.abort(); } catch (e) { /* ignore */ }
  }
  DemoState.currentAbortController = null;
  hideStreamError();
  updateStreamButtonStates();
  updateStatusUI();
}

function resetDemoState() {
  stopStream();
  DemoState.totalPredictions = 0;
  DemoState.fraudCount = 0;
  DemoState.legitimateCount = 0;
  DemoState.latencies = [];
  DemoState.feedItems = [];
  DemoState.probabilities = [];
  DemoState.lastThreshold = null;
  DemoState.lastProbability = null;
  DemoState.lastModelVersion = null;
  DemoState.consecutiveErrors = 0;
  hideStreamError();
  updateDemoDisplay();
}

function setStreamSpeed(multiplier) {
  DemoState.speedMultiplier = multiplier;
  
  // Update button UI
  document.querySelectorAll('[data-stream-speed]').forEach(btn => {
    const btnSpeed = parseInt(btn.dataset.streamSpeed);
    if (btnSpeed === multiplier) {
      btn.classList.add('speed-active');
    } else {
      btn.classList.remove('speed-active');
    }
  });
}

function updateStreamButtonStates() {
  const isRunning = DemoState.isRunning;
  
  if (DemoState.startDatasetBtn) {
    DemoState.startDatasetBtn.disabled = isRunning;
  }
  if (DemoState.startRandomBtn) {
    DemoState.startRandomBtn.disabled = isRunning;
  }
  if (DemoState.pauseBtn) {
    DemoState.pauseBtn.disabled = !isRunning;
    DemoState.pauseBtn.textContent = DemoState.isPaused ? 'Resume' : 'Pause';
  }
  if (DemoState.stopBtn) {
    DemoState.stopBtn.disabled = !isRunning;
  }
}

// ====================================================================
// MAIN STREAMING LOOP
// ====================================================================

async function runPredictionStream() {
  while (DemoState.isRunning) {
    // Handle pause
    if (DemoState.isPaused) {
      await sleep(100);
      continue;
    }
    
    try {
      // Get next transaction
      const transaction = DemoState.mode === 'dataset'
        ? getNextDatasetTransaction()
        : generateRandomTransaction();

      if (!transaction || !Array.isArray(transaction.features) || transaction.features.length !== 30) {
        throw new Error('Transaction generator returned invalid feature vector (expected 30 floats).');
      }
      
      // Make prediction
      const prediction = await makePredictionForStream(transaction);
      
      if (prediction) {
        // Update state
        updatePredictionStats(prediction);
        addFeedItem(prediction);
        updateDemoDisplay();
        DemoState.consecutiveErrors = 0;
        hideStreamError();

        DemoState.lastThreshold = prediction.threshold;
        DemoState.lastProbability = prediction.probability;
        DemoState.lastModelVersion = prediction.model_version;
        updateStatusUI();
      }
      
    } catch (error) {
      console.error('Stream prediction error:', error);
      DemoState.consecutiveErrors++;
      showStreamError(error && error.message ? error.message : String(error));

      // If the backend is down or consistently failing, pause the stream (demo-friendly).
      if (DemoState.consecutiveErrors >= 5) {
        DemoState.isPaused = true;
        DemoState.status = 'error';
        updateStreamButtonStates();
        updateStatusUI();
      }
    }
    
    // Wait before next prediction
    const delayMs = DemoState.baseDelayMs / DemoState.speedMultiplier;
    await sleep(delayMs);
  }
}

// ====================================================================
// API CALLS
// ====================================================================

async function makePredictionForStream(transaction) {
  const startTime = performance.now();
  const apiUrl = (typeof getApiUrl === 'function') ? getApiUrl() : 'http://localhost:8000';

  const controller = new AbortController();
  DemoState.currentAbortController = controller;
  
  try {
    const response = await fetch(`${apiUrl}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ features: transaction.features }),
      signal: controller.signal,
    });
    
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        if (err && err.detail) detail = String(err.detail);
      } catch (e) {
        // ignore json parse errors
      }
      throw new Error(`API error: ${detail}`);
    }
    
    const result = await response.json();
    if (
      !result ||
      typeof result.fraud_probability !== 'number' ||
      (result.fraud_label !== 0 && result.fraud_label !== 1) ||
      typeof result.threshold !== 'number' ||
      typeof result.model_version !== 'string' ||
      typeof result.request_id !== 'string'
    ) {
      throw new Error('Invalid /predict response shape (missing required fields).');
    }

    const endTime = performance.now();
    const latency = endTime - startTime;
    
    return {
      txn_time_s: transaction.features[0],
      amount: transaction.amount,
      probability: result.fraud_probability,
      label: result.fraud_label,
      threshold: result.threshold,
      model_version: result.model_version,
      request_id: result.request_id,
      latency: latency
    };
    
  } catch (error) {
    if (error && error.name === 'AbortError') {
      return null;
    }
    throw error;
  } finally {
    if (DemoState.currentAbortController === controller) {
      DemoState.currentAbortController = null;
    }
  }
}

// ====================================================================
// STATE UPDATES
// ====================================================================

function updatePredictionStats(prediction) {
  DemoState.totalPredictions++;
  
  if (prediction.label === 1) {
    DemoState.fraudCount++;
  } else {
    DemoState.legitimateCount++;
  }
  
  DemoState.latencies.push(prediction.latency);
  if (DemoState.latencies.length > 1000) {
    DemoState.latencies.shift(); // Keep last 1000 for avg
  }

  DemoState.probabilities.push(prediction.probability);
  if (DemoState.probabilities.length > 1000) {
    DemoState.probabilities.shift();
  }
}

function addFeedItem(prediction) {
  const item = {
    txnTime: formatTxnTime(prediction.txn_time_s),
    amount: prediction.amount.toFixed(2),
    probability: (prediction.probability * 100).toFixed(1),
    label: prediction.label === 1 ? 'FRAUD' : 'LEGIT',
    isFraud: prediction.label === 1,
    threshold: prediction.threshold.toFixed(2),
    latency: prediction.latency.toFixed(1),
    requestId: prediction.request_id
  };
  
  DemoState.feedItems.push(item); // Append-only (newest at bottom)
  
  if (DemoState.feedItems.length > DemoState.maxFeedItems) {
    DemoState.feedItems.shift(); // Remove oldest from front
  }
}

// ====================================================================
// DISPLAY UPDATES
// ====================================================================

function updateDemoDisplay() {
  updateCounters();
  updateFeed();
}

function updateCounters() {
  if (DemoState.totalCountEl) {
    DemoState.totalCountEl.textContent = DemoState.totalPredictions;
  }
  
  if (DemoState.fraudCountEl) {
    DemoState.fraudCountEl.textContent = DemoState.fraudCount;
  }
  
  if (DemoState.legitCountEl) {
    DemoState.legitCountEl.textContent = DemoState.legitimateCount;
  }
  
  // Fraud Rate
  if (DemoState.fraudRateEl) {
    const rate = DemoState.totalPredictions > 0
      ? ((DemoState.fraudCount / DemoState.totalPredictions) * 100).toFixed(2)
      : '0.00';
    DemoState.fraudRateEl.textContent = rate + '%';
  }
  
  // Average Latency
  if (DemoState.avgLatencyEl) {
    const avgLatency = DemoState.latencies.length > 0
      ? (DemoState.latencies.reduce((a, b) => a + b) / DemoState.latencies.length).toFixed(2)
      : '0.00';
    DemoState.avgLatencyEl.textContent = avgLatency + ' ms';
  }

  if (DemoState.avgProbEl) {
    const avgProb = DemoState.probabilities.length > 0
      ? (DemoState.probabilities.reduce((a, b) => a + b, 0) / DemoState.probabilities.length)
      : 0.0;
    DemoState.avgProbEl.textContent = (avgProb * 100).toFixed(2) + '%';
  }

  if (DemoState.lastThrEl) {
    DemoState.lastThrEl.textContent = DemoState.lastThreshold === null ? '-' : String(DemoState.lastThreshold.toFixed(4));
  }

  if (DemoState.lastProbEl) {
    DemoState.lastProbEl.textContent = DemoState.lastProbability === null ? '-' : String((DemoState.lastProbability * 100).toFixed(3) + '%');
  }
}

function updateFeed() {
  if (!DemoState.feedContainer) return;
  
  if (DemoState.feedItems.length === 0) {
    DemoState.feedContainer.innerHTML = '<div class="demo-feed-empty">Waiting for predictions...</div>';
    return;
  }
  
  const html = DemoState.feedItems.map(item => `
    <div class="demo-feed-item ${item.isFraud ? 'demo-fraud' : 'demo-legitimate'}">
      <div class="demo-feed-time">${item.txnTime}</div>
      <div class="demo-feed-amount">$${item.amount}</div>
      <div class="demo-feed-prob">${item.probability}%</div>
      <div class="demo-feed-label">${item.label}</div>
      <div class="demo-feed-latency">${item.threshold}</div>
      <div class="demo-feed-request">${escapeHtml(item.requestId)}</div>
    </div>
  `).join('');
  
  DemoState.feedContainer.innerHTML = html;
  DemoState.feedContainer.scrollTop = DemoState.feedContainer.scrollHeight;

  drawProbabilityChart();
}

// ====================================================================
// UTILITY FUNCTIONS
// ====================================================================

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function formatTxnTime(txnTimeS) {
  if (typeof txnTimeS !== 'number' || !isFinite(txnTimeS)) return '-';
  return `t+${Math.round(txnTimeS)}s`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function updateStatusUI() {
  if (DemoState.statusEl) DemoState.statusEl.textContent = DemoState.status;
  if (DemoState.modeEl) DemoState.modeEl.textContent = DemoState.mode;
  if (DemoState.modelVersionEl && DemoState.lastModelVersion) {
    DemoState.modelVersionEl.textContent = DemoState.lastModelVersion;
  }
}

function showStreamError(message) {
  if (DemoState.errorTextEl) DemoState.errorTextEl.textContent = message;
  if (DemoState.errorBannerEl) DemoState.errorBannerEl.style.display = 'flex';
}

function hideStreamError() {
  if (DemoState.errorBannerEl) DemoState.errorBannerEl.style.display = 'none';
  if (DemoState.errorTextEl) DemoState.errorTextEl.textContent = '-';
}

function drawProbabilityChart() {
  const ctx = DemoState.chartCtx;
  const canvas = DemoState.chartCanvas;
  if (!ctx || !canvas) return;

  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  // Frame
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

  const values = DemoState.feedItems.map(it => parseFloat(it.probability) / 100.0).filter(v => isFinite(v));
  const n = values.length;
  if (n < 2) return;

  const padding = 14;
  const plotW = width - padding * 2;
  const plotH = height - padding * 2;

  // Threshold line (latest known)
  const thr = DemoState.lastThreshold;
  if (typeof thr === 'number' && isFinite(thr)) {
    const yThr = padding + (1.0 - clamp01(thr)) * plotH;
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = '#f59e0b';
    ctx.beginPath();
    ctx.moveTo(padding, yThr);
    ctx.lineTo(width - padding, yThr);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Line plot
  ctx.strokeStyle = '#4f46e5';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padding + (i / (n - 1)) * plotW;
    const y = padding + (1.0 - clamp01(values[i])) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Last point
  const lastX = padding + plotW;
  const lastY = padding + (1.0 - clamp01(values[n - 1])) * plotH;
  ctx.fillStyle = '#111827';
  ctx.beginPath();
  ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
  ctx.fill();
}

function clamp01(x) {
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}

// ====================================================================
// INITIALIZATION ON PAGE LOAD
// ====================================================================

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeStreamingDemo);
} else {
  initializeStreamingDemo();
}
