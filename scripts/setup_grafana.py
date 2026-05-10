import requests
import json
import sys

GRAFANA_URL = "http://localhost:3000"
AUTH = ("admin", "Cyberarmy@123")

def setup():
    dashboard_json = {
      "uid": "fastapi_ultimate_1",
      "title": "FastAPI Observability (Official SupportPulse)",
      "tags": [ "fastapi", "supportpulse" ],
      "timezone": "browser",
      "schemaVersion": 36,
      "version": 1,
      "refresh": "5s",
      "panels": [
        {
          "type": "stat",
          "title": "Total API Requests (Last 15m)",
          "gridPos": { "h": 5, "w": 6, "x": 0, "y": 0 },
          "targets": [{"expr": "sum(increase(http_requests_total[15m]))"}],
          "options": {"colorMode": "value", "graphMode": "area"}
        },
        {
          "type": "stat",
          "title": "4xx Client Errors",
          "gridPos": { "h": 5, "w": 6, "x": 6, "y": 0 },
          "targets": [{"expr": "sum(increase(http_requests_total{status=~\"4..\"}[15m]))"}],
          "options": {"colorMode": "background", "graphMode": "none"}
        },
        {
          "type": "stat",
          "title": "5xx Server Errors",
          "gridPos": { "h": 5, "w": 6, "x": 12, "y": 0 },
          "targets": [{"expr": "sum(increase(http_requests_total{status=~\"5..\"}[15m]))"}],
          "options": {"colorMode": "background", "graphMode": "none"}
        },
        {
          "type": "stat",
          "title": "Avg Latency (ms)",
          "gridPos": { "h": 5, "w": 6, "x": 18, "y": 0 },
          "targets": [{"expr": "(sum(rate(http_request_duration_seconds_sum[15m])) / sum(rate(http_request_duration_seconds_count[15m]))) * 1000"}],
          "options": {"colorMode": "value", "graphMode": "area"}
        },
        {
          "type": "timeseries",
          "title": "Requests per Second by Endpoint",
          "gridPos": { "h": 8, "w": 12, "x": 0, "y": 5 },
          "targets": [
            { "expr": "sum(rate(http_requests_total[1m])) by (handler)", "legendFormat": "{{handler}}" }
          ],
          "options": {"tooltip": {"mode": "multi"}}
        },
        {
          "type": "timeseries",
          "title": "Requests by Status Code",
          "gridPos": { "h": 8, "w": 12, "x": 12, "y": 5 },
          "targets": [
            { "expr": "sum(rate(http_requests_total[1m])) by (status)", "legendFormat": "HTTP {{status}}" }
          ],
          "options": {"tooltip": {"mode": "multi"}}
        },
        {
          "type": "timeseries",
          "title": "Response Time (Seconds)",
          "gridPos": { "h": 8, "w": 24, "x": 0, "y": 13 },
          "targets": [
            { "expr": "sum(rate(http_request_duration_seconds_sum[1m])) by (handler) / sum(rate(http_request_duration_seconds_count[1m])) by (handler)", "legendFormat": "{{handler}}" }
          ],
          "options": {"tooltip": {"mode": "multi"}}
        }
      ]
    }
    
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
