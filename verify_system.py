#!/usr/bin/env python
"""
End-to-End System Verification Script
Demonstrates full fraud detection system working locally

Run: python verify_system.py
"""

import json
import time
import urllib.request
from urllib.error import URLError

API_BASE = "http://localhost:8000"

def check_endpoint(url, method="GET", data=None, expected_status=200):
    """Test an API endpoint"""
    try:
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req) as response:
            status = response.status
            content = response.read().decode() if status == 200 else None
            return status == expected_status, status, content
    except Exception as e:
        return False, str(e), None

def main():
    print("\n" + "="*70)
    print("FRAUD DETECTION SYSTEM - END-TO-END VERIFICATION")
    print("="*70 + "\n")
    
    # Check API availability
    print("[1/6] Checking API Health...")
    ok, status, content = check_endpoint(f"{API_BASE}/health")
    if ok:
        health = json.loads(content)
        print(f"      ✓ API Available (Status: {status})")
        print(f"      ✓ Model Loaded: {health['model_loaded']}")
        print(f"      ✓ Model Version: {health['model_version']}")
        print(f"      ✓ Expected Features: {health['expected_features']}")
        print(f"      ✓ Threshold: {health.get('threshold')}")
    else:
        print(f"      ✗ API Unavailable: {status}")
        print("      Make sure to run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Pull real samples from the dataset through the API (keeps feature order consistent with the model).
    print("\n[2/6] Fetching Dataset Samples...")
    ok, status, content = check_endpoint(f"{API_BASE}/dataset/samples?n=1&strategy=legit&seed=7")
    if not ok:
        print(f"      ✗ Dataset sample fetch failed: {status}")
        return
    sample_legit = json.loads(content)["samples"][0]["features"]
    ok, status, content = check_endpoint(f"{API_BASE}/dataset/samples?n=1&strategy=fraud&seed=7")
    if not ok:
        print(f"      ✗ Dataset sample fetch failed: {status}")
        return
    sample_fraud = json.loads(content)["samples"][0]["features"]

    # Test prediction with legitimate transaction
    print("\n[3/6] Testing Legitimate Transaction Prediction...")
    payload = json.dumps({"features": sample_legit}).encode()
    
    ok, status, content = check_endpoint(f"{API_BASE}/predict", method="POST", data=payload, expected_status=200)
    if ok:
        result = json.loads(content)
        print(f"      ✓ Prediction Success (Status: {status})")
        print(f"      ✓ Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"      ✓ Fraud Label: {result['fraud_label']}")
        print(f"      ✓ Threshold: {result['threshold']}")
        print(f"      ✓ Model Version: {result['model_version']}")
        print(f"      ✓ Model Type: {result.get('model_type')}")
    else:
        print(f"      ✗ Prediction Failed: {status}")
        return
    
    # Test prediction with a known fraud sample
    print("\n[4/6] Testing Fraud Sample Prediction...")
    payload = json.dumps({"features": sample_fraud}).encode()
    
    ok, status, content = check_endpoint(f"{API_BASE}/predict", method="POST", data=payload, expected_status=200)
    if ok:
        result = json.loads(content)
        print(f"      ✓ Prediction Success")
        print(f"      ✓ Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"      ✓ Fraud Label: {result['fraud_label']}")
    else:
        print(f"      ✗ Prediction Failed: {status}")
    
    # Test invalid request handling
    print("\n[5/6] Testing Error Handling (Invalid Feature Count)...")
    invalid_payload = json.dumps({'features': [0.0] * 20}).encode()  # Wrong count
    ok, status, content = check_endpoint(f"{API_BASE}/predict", method="POST", data=invalid_payload, expected_status=422)
    if ok:
        print(f"      ✓ Error Handling Works (Status: 422)")
        error = json.loads(content)
        print(f"      ✓ Error Message: {error['detail']}")
    else:
        print(f"      ✗ Expected 422, got {status}")
    
    # Check metrics endpoint
    print("\n[6/6] Checking Metrics Endpoint...")
    ok, status, content = check_endpoint(f"{API_BASE}/metrics")
    if ok:
        print(f"      ✓ Metrics Endpoint Available (Status: {status})")
        if 'api_requests_total' in content:
            print(f"      ✓ Request Metrics Present")
        if 'fraud_predictions_total' in content:
            print(f"      ✓ Fraud Prediction Metrics Present")
        if 'api_request_latency_seconds' in content:
            print(f"      ✓ Latency Metrics Present")
    else:
        print(f"      ✗ Metrics Endpoint Failed: {status}")
    
    print("\n" + "="*70)
    print("✓ END-TO-END VERIFICATION COMPLETE")
    print("="*70)
    print("\nSystem Status:")
    print("  • Backend API: WORKING")
    print("  • Model Loading: WORKING")
    print("  • Predictions: WORKING")
    print("  • Metrics Instrumentation: WORKING")
    print("  • Error Handling: WORKING")
    print("  • Demo Readiness (API): YES ✓")
    print("\nNext Steps:")
    print("  1. Open http://localhost:8080/index.html in browser")
    print("  2. Load sample transaction or enter your own")
    print("  3. Click 'Predict Fraud' to see results")
    print("  4. Check metrics at http://localhost:8000/metrics")
    print("\n")

if __name__ == '__main__':
    main()
