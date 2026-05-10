import requests
import json
import sys

GRAFANA_URL = "http://localhost:3000"
AUTH = ("admin", "Cyberarmy@123")

def setup():
    # 1. Add Prometheus Data Source
    ds_payload = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://localhost:9090",
        "access": "proxy",
        "isDefault": True
    }
    
    print("Setting up Prometheus data source...")
    resp = requests.post(f"{GRAFANA_URL}/api/datasources", json=ds_payload, auth=AUTH)
    if resp.status_code in [200, 409]:
        print("Prometheus data source configured successfully.")
    else:
        print(f"Failed to configure data source: {resp.text}")
        return
        
    # 2. Create Custom FastAPI Dashboard JSON
    dashboard_json = {
      "uid": "fastapi_custom_1",
      "title": "SupportPulse FastAPI Observability",
      "tags": [ "fastapi", "supportpulse" ],
      "timezone": "browser",
      "schemaVersion": 36,
      "version": 1,
      "refresh": "5s",
      "panels": [
        {
          "type": "timeseries",
          "title": "Total API Requests (5m)",
          "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
          "targets": [
            { "expr": "sum(increase(http_requests_total[5m])) by (handler)", "legendFormat": "{{handler}}" }
          ]
        },
        {
          "type": "timeseries",
          "title": "Average Request Duration (seconds)",
          "gridPos": { "h": 8, "w": 12, "x": 12, "y": 0 },
          "targets": [
            { "expr": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])", "legendFormat": "{{handler}}" }
          ]
        },
        {
          "type": "stat",
          "title": "Active Requests In Progress",
          "gridPos": { "h": 6, "w": 24, "x": 0, "y": 8 },
          "targets": [
            { "expr": "sum(http_requests_in_progress)" }
          ]
        }
      ]
    }
    
    # 3. Import Dashboard
    print("Importing custom FastAPI Dashboard...")
    import_payload = {
        "dashboard": dashboard_json,
        "overwrite": True
    }
    dash_resp = requests.post(f"{GRAFANA_URL}/api/dashboards/db", json=import_payload, auth=AUTH)
    
    if dash_resp.status_code == 200:
        print("Success! Dashboard is now available in Grafana.")
        print("URL:", dash_resp.json().get("url"))
    else:
        print(f"Failed to import dashboard: {dash_resp.text}")

if __name__ == "__main__":
    setup()
