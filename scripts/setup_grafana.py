import requests
import json

GRAFANA_URL = "http://localhost:3000"
PASSWORDS = ["Cyberarmy@123", "cyberarmy@123", "admin"]

def try_auth():
    for pwd in PASSWORDS:
        resp = requests.get(f"{GRAFANA_URL}/api/datasources", auth=("admin", pwd))
        if resp.status_code == 200:
            return ("admin", pwd)
    return None

def setup():
    auth = try_auth()
    if not auth:
        print("Failed to authenticate with any password.")
        return
        
    print(f"Authenticated with password: {auth[1]}")
    
    # 1. Add Prometheus Data Source
    ds_payload = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "access": "proxy",
        "isDefault": True
    }
    
    print("Setting up Prometheus data source...")
    resp = requests.post(f"{GRAFANA_URL}/api/datasources", json=ds_payload, auth=auth)
    if resp.status_code in [200, 409]:
        print("Prometheus data source configured successfully.")
    else:
        print(f"Failed to configure data source: {resp.text}")
        
    # 2. Download Dashboard 16358
    print("Downloading FastAPI Dashboard template from Grafana.com...")
    req = requests.get("https://grafana.com/api/dashboards/16358/revisions/1/download")
    if req.status_code != 200:
        print("Failed to download dashboard.")
        return
        
    dashboard_json = req.json()
    dashboard_json["id"] = None
    dashboard_json["uid"] = "fastapi-monitoring"
    
    # 3. Import Dashboard
    print("Importing Dashboard into your local Grafana...")
    import_payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}]
    }
    dash_resp = requests.post(f"{GRAFANA_URL}/api/dashboards/import", json=import_payload, auth=auth)
    
    if dash_resp.status_code == 200:
        print("Success! Dashboard is now available in Grafana.")
    else:
        print(f"Failed to import dashboard: {dash_resp.text}")

if __name__ == "__main__":
    setup()
