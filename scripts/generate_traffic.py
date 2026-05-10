import requests
import time
import random
import threading

API_BASE = "http://localhost:8000"

def blast_traffic():
    print("🚀 Pumping 200 high-speed fake requests to populate Grafana...")
    
    def make_request():
        # 70% success, 20% 404, 10% 422
        choice = random.random()
        try:
            if choice < 0.7:
                requests.get(f"{API_BASE}/health", timeout=2)
            elif choice < 0.9:
                requests.get(f"{API_BASE}/api/v1/fake-endpoint-to-trigger-404", timeout=2)
            else:
                # Trigger a 422 Unprocessable Entity by sending empty body
                requests.post(f"{API_BASE}/api/v1/triage", json={}, timeout=2)
        except:
            pass

    threads = []
    for _ in range(200):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()
        time.sleep(0.02)  # tiny delay to spread them out slightly
        
    for t in threads:
        t.join()
        
    print("✅ Done! Traffic pumped. Refresh Grafana now!")

if __name__ == "__main__":
    blast_traffic()
