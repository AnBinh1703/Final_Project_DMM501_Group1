import json
import urllib.request

# Sample transaction data (legitimate)
sample_features = [
    0.0,  # Time
    -1.36, -0.07, 2.54, 1.38, -0.34, 0.46, 0.24, 0.10, 0.36, 0.09, -0.55, -0.62, -0.99, -0.31, 1.47, -0.47, 0.21, 0.03, 0.40,
    0.25, -0.02, 0.28, -0.11, 0.07, 0.13, -0.19, 0.13, -0.02,  # V1 to V28
    149.62  # Amount
]

payload = json.dumps({'features': sample_features}).encode('utf-8')

# Test 1: Legitimate transaction
print('TEST 1: Legitimate Transaction')
req = urllib.request.Request('http://localhost:8000/predict', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Status: {response.status}")
        print(f"Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"Fraud Label: {result['fraud_label']}")
        print(f"Threshold: {result['threshold']}")
        print(f"Model Version: {result['model_version']}")
        print("✓ Frontend can call API successfully\n")
except Exception as e:
    print(f"✗ Error: {e}\n")

# Test 2: Suspicious transaction (high-value)
print('TEST 2: High-Value Transaction (Suspicious)')
sample_features[29] = 500.0  # High amount
suspicious_payload = json.dumps({'features': sample_features}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/predict', data=suspicious_payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Status: {response.status}")
        print(f"Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"Fraud Label: {result['fraud_label']}")
        print("✓ Different transaction gives different prediction\n")
except Exception as e:
    print(f"✗ Error: {e}\n")

print("FRONTEND-TO-API INTEGRATION TEST COMPLETE")
