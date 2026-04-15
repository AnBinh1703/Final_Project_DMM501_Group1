/* global window */

// Demo data used for MODE 1 — Real Sample Stream.
//
// IMPORTANT:
// - Every entry below is a full feature vector of EXACTLY 30 floats.
// - Feature order matches backend contract: [Time, V1..V28, Amount]
//
// The samples are extracted from the local `data/archive/creditcard.csv` dataset in this repo.

(function () {
  const INLINE_REAL_SAMPLES = [
    {"features":[20329.0,1.0984177990865,-0.443084606008526,1.00086919134106,-0.724004624917936,-0.746183108028505,0.484721866872625,-0.933337876099331,0.328263447409737,2.88872694389505,-1.36545269314961,2.60207388670277,-1.08307565642334,1.13582513735214,1.60987520386193,0.379274420987025,-0.848750906112306,0.919340503309758,0.0943746355339732,-0.0829340710114736,-0.221714516686603,-0.0523822025568373,0.338629454558602,0.0184905161590614,-0.332702170046793,0.283946455573,-0.069650803965727,0.178675053839213,0.176601853810823,-0.0590518027393107,2.5]},
    {"features":[132450.0,-0.881072392877743,0.263099815678994,0.911107885257001,-1.07924545639837,-0.430226422778796,0.292752213696768,0.0767560669656776,0.287035761119171,-0.247731901932745,-0.102264984923216,0.241276112773584,0.58958269339218,-0.431736279315848,0.318439918662831,0.559642610388253,-0.869799576713944,-0.158194819207038,-0.350560072967529,-0.741210592004773,-0.0166625956098434,-0.116570111506823,0.328888242168323,-0.259879445967798,-0.206173902994194,-0.499283083279962,0.0262073645067179,-0.0336222457347718,0.0486310798813236,0.0190174979169015,7.0]},
    {"features":[63560.0,-0.641539713294617,0.996858068607746,1.61022470241577,0.0173715546387313,0.230031135394604,0.258673616237356,0.334506488023034,0.196087616427984,-0.745025592519774,-0.77857690667534,0.972045320074066,0.437666511603682,-0.451693184232407,0.372831171219398,-0.00772242201711603,0.683900637144793,-0.47986570648746,0.172802410843975,-0.192968293717479,-0.0467898929194778,0.0701020087758415,0.495584505084303,-0.0840227755667738,-0.149727467042802,-0.576124721039922,0.117142463827965,-0.23716866134697,0.0606568739140435,0.0817212315953554,2.99]}
  ];

  let _realSamples = null;

  let realIndex = 0;
  let randomTimeCursor = 0;

  function reset() {
    realIndex = 0;
    randomTimeCursor = 0;
  }

  async function ensureRealSamplesLoaded() {
    if (Array.isArray(_realSamples) && _realSamples.length > 0) return _realSamples;
    _realSamples = INLINE_REAL_SAMPLES.map(s => ({ features: s.features, amount: s.features[29], time_s: s.features[0] }));
    return _realSamples;
  }

  async function getNextRealTransaction() {
    const pool = await ensureRealSamplesLoaded();
    const item = pool[realIndex % pool.length];
    realIndex += 1;
    const features = item.features.map(Number);
    if (features.length !== 30 || features.some(v => !Number.isFinite(v))) {
      throw new Error('Real sample is malformed (expected 30 finite numbers).');
    }
    return {
      source: 'real',
      features,
      time_s: (typeof item.time_s === 'number') ? item.time_s : features[0],
      amount: (typeof item.amount === 'number') ? item.amount : features[29],
    };
  }

  // ------------------------------------------------------------------
  // MODE 2 — Random Generated Stream
  // ------------------------------------------------------------------
  //
  // Goal: realistic-enough traffic (not pure meaningless noise) while still being
  // valid for the backend contract.
  //
  // Strategy:
  // - Time: monotonic-ish cursor + jitter
  // - V1..V28: mostly N(0,1) with occasional heavier-tail events
  // - Amount: log-normal-ish, occasionally large values; sometimes inject stress/anomaly

  function randn() {
    let u1 = 0;
    let u2 = 0;
    while (u1 === 0) u1 = Math.random();
    while (u2 === 0) u2 = Math.random();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }

  function logNormal(mu, sigma) {
    return Math.exp(mu + sigma * randn());
  }

  function generateRandomTransaction() {
    // time cursor: start around 0..10k, then increment 0.2..2.5 seconds per tick
    if (randomTimeCursor <= 0) randomTimeCursor = Math.random() * 10000;
    randomTimeCursor += 0.2 + Math.random() * 2.3;
    const time = randomTimeCursor + (Math.random() - 0.5) * 0.25;

    const stress = Math.random() < 0.06; // ~6% more dramatic samples (demo-friendly)
    const tailEvent = Math.random() < 0.03;

    const v = [];
    for (let i = 0; i < 28; i++) {
      let x = randn();
      if (tailEvent) x += randn() * 2.2;
      if (stress) x += randn() * 1.2;
      v.push(x);
    }

    // Amount: mostly small/moderate, occasionally large; stress pushes higher.
    let amount = logNormal(3.4, 0.85); // typical ~$30-ish median with a long tail
    if (Math.random() < 0.05) amount *= 8; // occasional high-value
    if (stress) amount *= 12;
    amount = Math.max(0.01, Math.min(amount, 5000));

    // Inject a high-value anomaly with slightly amplified feature magnitudes.
    if (stress && Math.random() < 0.35) {
      amount = Math.max(amount, 750 + Math.random() * 2250);
      for (let i = 0; i < v.length; i++) v[i] *= 1.35 + Math.random() * 0.5;
    }

    const features = [time, ...v, amount];
    return { source: 'random', features, time_s: time, amount };
  }

  window.DemoData = {
    reset,
    ensureRealSamplesLoaded,
    getNextRealTransaction,
    generateRandomTransaction,
    realSampleCount: null,
  };
})();
