import time
import random
import requests
import json
import threading

API_URL = "http://127.0.0.1:5000/api/analyze"
RUNNING = True

# Some realistic looking dummy IPs
SOURCES = ["192.168.1.10", "192.168.1.55", "10.0.0.5", "10.0.0.22", "172.16.0.4", "8.8.8.8", "144.22.1.9", "45.33.2.1"]
DESTINATIONS = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "192.168.1.100"]

def generate_packet(features):
    packet = {
        "source": random.choice(SOURCES),
        "destination": random.choice(DESTINATIONS),
        "protocol": random.choice(["tcp", "udp", "icmp"])
    }
    
    # We don't know exactly what features the model needs, so we fetch them first.
    # The actual numerical values might not trigger a 'real' attack prediction unless they match the training data,
    # but the ML model will predict *something* (Normal/Attack/Suspicious) based on these random inputs.
    
    # Bias slightly towards normal traffic
    is_attack = random.random() < 0.2 
    
    for feat in features:
        if feat == "duration":
            packet[feat] = random.uniform(0, 100) if is_attack else 0.0
        elif feat == "src_bytes":
            packet[feat] = random.randint(0, 50000) if is_attack else random.randint(40, 400)
        elif feat == "dst_bytes":
            packet[feat] = random.randint(0, 50000) if is_attack else random.randint(40, 8000)
        elif "count" in feat:
            packet[feat] = random.randint(100, 500) if is_attack else random.randint(1, 10)
        elif "rate" in feat:
            packet[feat] = random.uniform(0.5, 1.0) if is_attack else random.uniform(0.0, 0.1)
        else:
            packet[feat] = random.uniform(0, 1)

    return packet

def simulate():
    print("Fetching model features...")
    try:
        res = requests.get("http://127.0.0.1:5000/api/model/features")
        data = res.json()
        if not data.get("data", {}).get("model_loaded"):
            print("ERROR: No model is loaded. Please upload a dataset and train a model first!")
            return
            
        features = data["data"]["features"]
        print(f"Model loaded with {len(features)} features. Starting simulation...")
        
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return

    req_count = 0
    while RUNNING:
        packet = generate_packet(features)
        try:
            r = requests.post(API_URL, json=packet)
            if r.status_code == 200:
                pred = r.json()["data"]["prediction"]
                risk = r.json()["data"]["risk_score"]
                req_count += 1
                print(f"[{req_count}] Sent packet -> Prediction: {pred.upper()} | Risk: {risk}")
            else:
                print(f"Error from server: {r.status_code} - {r.text}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            
        # Sleep for a random interval between 1 and 4 seconds
        time.sleep(random.uniform(1.0, 4.0))

if __name__ == "__main__":
    print("==================================================")
    print(" OmniShield AI - Live Traffic Simulator")
    print("==================================================")
    print("Press Ctrl+C to stop.")
    
    try:
        simulate()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        RUNNING = False
