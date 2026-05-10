import requests
import json
import sys

GRAFANA_URL = "http://localhost:3000"
AUTH = ("admin", "Cyberarmy@123")

def setup():
    print("Downloading the OFFICIAL FastAPI Observability Dashboard from Grafana.com...")
    req = requests.get("https://grafana.com/api/dashboards/16358/revisions/1/download")
    if req.status_code != 200:
        print("Failed to download dashboard.")
        return
        
    dashboard_json = req.json()
    
    # Grafana 16358 uses a template variable for the data source.
    # We must explicitly define it in the import payload.
    dashboard_json["id"] = None
    dashboard_json["uid"] = "fastapi-official-16358"
    dashboard_json["title"] = "FastAPI Observability (Official)"
    
    print("Importing Dashboard into your local Grafana...")
    import_payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "inputs": [
            {
                "name": "DS_PROMETHEUS-K8S-BBOX",
                "type": "datasource",
                "pluginId": "prometheus",
                "value": "Prometheus"
            }
        ]
    }
    
    dash_resp = requests.post(f"{GRAFANA_URL}/api/dashboards/import", json=import_payload, auth=AUTH)
    
    if dash_resp.status_code == 200:
        print("Success! Official Dashboard is now available in Grafana.")
        print("URL:", f"{GRAFANA_URL}/d/fastapi-official-16358/fastapi-observability-official")
    else:
        print(f"Failed to import dashboard: {dash_resp.status_code} - {dash_resp.text}")

if __name__ == "__main__":
    setup()
