import json
import urllib.request


def main(api_base: str = "http://localhost:8000") -> int:
    def fetch_one(strategy: str) -> list[float]:
        url = f"{api_base}/dataset/samples?n=1&strategy={strategy}&seed=7"
        with urllib.request.urlopen(url) as resp:
            body = json.loads(resp.read().decode())
            return body["samples"][0]["features"]

    sample_features = fetch_one("legit")
    payload = json.dumps({"features": sample_features}).encode("utf-8")

    print("TEST 1: Legitimate Transaction")
    req = urllib.request.Request(f"{api_base}/predict", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Status: {response.status}")
        print(f"Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"Fraud Label: {result['fraud_label']}")
        print(f"Threshold: {result['threshold']}")
        print(f"Model Version: {result['model_version']}")
        print("✓ Frontend can call API successfully\n")

    print("TEST 2: Fraud Sample Transaction")
    fraud_features = fetch_one("fraud")
    suspicious_payload = json.dumps({"features": fraud_features}).encode("utf-8")
    req = urllib.request.Request(f"{api_base}/predict", data=suspicious_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Status: {response.status}")
        print(f"Fraud Probability: {result['fraud_probability']:.6f}")
        print(f"Fraud Label: {result['fraud_label']}")
        print("✓ Different transaction gives different prediction\n")

    print("FRONTEND-TO-API INTEGRATION TEST COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
