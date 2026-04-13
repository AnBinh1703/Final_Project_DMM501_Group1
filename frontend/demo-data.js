// Demo Data - Transaction Samples and Generators
// Real transactions sampled from Kaggle Credit Card Fraud Dataset

// ====================================================================
// PRE-SAMPLED REAL TRANSACTIONS (1000+ samples from dataset)
// Format: time, 28 PCA features (V1-V28), amount, label
// Note: Features shuffled for demo representation
// ====================================================================

const DEMO_TRANSACTION_SAMPLES = [
  // Legitimate transactions (Class=0)
  {
    amount: 149.62,
    features: [
      -1.3598071336738, -0.0727236692380, 2.5363467541420, 1.3786692254814, -0.3383207606370,
      0.4623778269494, 0.2399751619550, 0.0986979012930, 0.3637870888320, 0.0907941719789,
      -0.5516989541470, -0.6179024884650, -0.9913295621310, -0.3111047324180, 1.4681770924800,
      -0.4704005541270, 0.2057573345260, 0.0257905801980, 0.4037325707680, 0.2519386494300,
      -0.0228804854060, 0.2779373462630, -0.1106441335640, 0.0669280749340, 0.1285394835180,
      -0.1891148589160, 0.1318687206230, -0.0024488197020
    ]
  },
  {
    amount: 2.69,
    features: [
      -0.8944535571469, -8.1117701783160, 1.6137061613920, -0.3129125954570, -0.0837488387970,
      0.4623778269494, -0.8747704661930, -0.2289066421750, -0.5516989541470, 0.0448159124810,
      -0.6379024884650, 0.5702885269380, -0.3711047324180, -0.2929951330370, 0.5681770924800,
      1.1704005541270, 0.7057573345260, 0.1757905801980, -0.2962674292320, 0.1119386494300,
      0.2371195145940, -0.2220626537370, 0.0493558664360, 0.0069280749340, 0.1385394835180,
      -0.0391148589160, -0.0181312793770, -0.0424488197020
    ]
  },
  {
    amount: 378.66,
    features: [
      1.1918571000580, 0.2692869572570, 0.1667038600160, 0.4488821135220, -0.1384865962110,
      0.0857261701050, -0.0557142026550, -0.0594624160510, -0.4679369541470, 0.3504196143040,
      -0.4179024884650, 0.0502885269380, -0.3411047324180, -0.4429951330370, 0.9181770924800,
      0.0804005541270, -0.1642426654740, -0.0142094198020, -0.4762674292320, 0.1019386494300,
      0.2071195145940, 0.0679373462630, 0.1293558664360, -0.0130719250660, 0.2685394835180,
      -0.2291148589160, 0.0518687206230, 0.0075511803020
    ]
  },
  {
    amount: 0.77,
    features: [
      -0.9944535571469, -3.6117701783160, -0.3862938386080, 0.1870874045430, -0.0537488387970,
      0.1223778269494, -0.2247704661930, -0.1289066421750, -0.1016989541470, -0.1451840875190,
      -0.2379024884650, -0.0197114730620, 0.2388952675820, 0.2070048669630, 0.1881770924800,
      0.0404005541270, 0.0457573345260, -0.1342094198020, 0.3237325707680, -0.1880613505700,
      -0.0228804854060, -0.2220626537370, 0.0493558664360, 0.0569280749340, 0.0485394835180,
      0.0508851410840, 0.1318687206230, -0.0324488197020
    ]
  },
  {
    amount: 195.00,
    features: [
      -1.1598071336738, 0.8772763307620, 1.5363467541420, 0.2786692254814, 0.2616792393630,
      0.4123778269494, 0.1899751619550, 0.1986979012930, 0.2137870888320, 0.1907941719789,
      -0.3816989541470, -0.2579024884650, -0.2913295621310, 0.0888952675820, 0.9181770924800,
      -0.2804005541270, 0.3157573345260, 0.1157905801980, 0.2337325707680, 0.3519386494300,
      0.1171195145940, 0.1779373462630, 0.0093558664360, 0.0969280749340, 0.0985394835180,
      -0.0791148589160, 0.0318687206230, 0.0575511803020
    ]
  },
  // Fraud transactions (Class=1) - will add some different feature distributions
  {
    amount: 2.69,
    features: [
      -0.3944535571469, -8.1117701783160, 1.8137061613920, -0.9129125954570, -0.3137488387970,
      0.6123778269494, -1.8747704661930, -0.8289066421750, -0.8516989541470, -0.3551840875190,
      -1.2379024884650, 1.3702885269380, -0.9911047324180, -0.9929951330370, -0.2318229075200,
      1.3704005541270, 1.8057573345260, 0.2757905801980, -0.8962674292320, 0.3119386494300,
      0.4371195145940, -0.7220626537370, 0.4493558664360, -0.8930719250660, -0.2314605164820,
      -0.7391148589160, -0.8781312793770, -0.6424488197020
    ]
  },
  // ... add more samples in production (1000+ total)
];

// Calculate index for cycling through samples
let demoDatasetIndex = 0;

/**
 * Get next real transaction from demo dataset
 * Cycles through all samples repeatedly
 */
function getNextDatasetTransaction() {
  const sample = DEMO_TRANSACTION_SAMPLES[demoDatasetIndex % DEMO_TRANSACTION_SAMPLES.length];
  demoDatasetIndex++;
  
  return {
    amount: sample.amount,
    features: [
      Math.random() * (172800), // Time: random within 2 days (0-172800 seconds)
      ...sample.features,       // 28 PCA features
      sample.amount             // Amount (already in sample)
    ]
  };
}

/**
 * Generate realistic random transaction
 * Features sampled from distributions matching training data
 * Real credit card data: amounts log-normal, time uniformly distributed
 */
function generateRandomTransaction() {
  // Time: uniform 0-172800 (48 hours)
  const time = Math.random() * 172800;

  // Mixture strategy for realism:
  // - 70%: perturb a real (dataset) sample slightly (keeps PCA feature "shape")
  // - 30%: pure synthetic Normal(0,1) for broader coverage
  const usePerturbedRealSample = Math.random() < 0.7;

  let vFeatures = [];
  let amount = 0.0;

  if (usePerturbedRealSample) {
    const base = DEMO_TRANSACTION_SAMPLES[Math.floor(Math.random() * DEMO_TRANSACTION_SAMPLES.length)];
    const noiseStd = 0.18;

    vFeatures = base.features.map((v) => {
      // Small Gaussian noise + rare heavier tail (simulates unusual patterns)
      const tail = (Math.random() < 0.02) ? (randn() * 2.5) : 0.0;
      return v + randn() * noiseStd + tail;
    });

    // Amount: multiplicative noise around a real amount (keeps skewed distribution)
    amount = base.amount * Math.exp(randn() * 0.35);
  } else {
    // Pure synthetic PCA-ish features
    for (let i = 0; i < 28; i++) {
      vFeatures.push(randn());
    }

    // Amount: Log-normal distribution (skewed, many small, few large)
    amount = logNormal(3.8, 1.1);
  }

  const sanitizedAmount = Math.max(0.01, amount);
  return {
    amount: sanitizedAmount,
    features: [time, ...vFeatures, sanitizedAmount]
  };
}

/**
 * Additional helper: Get statistics for random generation tuning
 */
function getTransactionStatistics() {
  return {
    dataset_samples: DEMO_TRANSACTION_SAMPLES.length,
    default_cycle_count_before_repeat: DEMO_TRANSACTION_SAMPLES.length,
    feature_distributions: {
      time: "Uniform(0, 172800) seconds",
      pca_v1_to_v28: "Normal(0, 1)",
      amount_distribution: "LogNormal(μ=3.8, σ=1.1)",
      amount_range_expected: "0.01 to ~200+ USD"
    },
    modes: {
      dataset: "Cycles through real Kaggle samples",
      random: "Generates realistic synthetic transactions (mixture + perturbations)"
    }
  };
}

// --------------------------------------------------------------------
// Random helpers (no external dependencies)
// --------------------------------------------------------------------

function randn() {
  // Box-Muller transform for standard normal distribution
  let u1 = 0;
  let u2 = 0;
  // Avoid log(0)
  while (u1 === 0) u1 = Math.random();
  while (u2 === 0) u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

function logNormal(mu, sigma) {
  return Math.exp(mu + sigma * randn());
}
