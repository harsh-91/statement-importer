# Created by Harsh (@harsh-91) | Made in India
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from statement_importer.access import create_api_key, list_api_keys, revoke_api_key, set_setting


def main():
    token = create_api_key("Automated smoke test")
    credential_id = list_api_keys()[0]["id"]
    client = app.test_client()
    headers = {"X-API-Key": token}
    try:
        set_setting("api_enabled", True)
        set_setting("mcp_enabled", True)
        health = client.get("/api/v1/health", headers=headers)
        transactions = client.get("/api/v1/transactions?page_size=3", headers=headers)
        csv_export = client.get("/api/v1/transactions?page_size=3&format=csv", headers=headers)
        mcp_initialize = client.post(
            "/mcp", headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        mcp_tools = client.post(
            "/mcp", headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert health.status_code == 200
        assert transactions.status_code == 200 and len(transactions.json["data"]) == 3
        assert transactions.json["total"] >= 4152
        assert csv_export.status_code == 200 and csv_export.mimetype == "text/csv"
        assert mcp_initialize.status_code == 200 and "protocolVersion" in mcp_initialize.json["result"]
        assert mcp_tools.status_code == 200 and len(mcp_tools.json["result"]["tools"]) >= 6
        print({
            "api_health": health.status_code,
            "api_total": transactions.json["total"],
            "csv": csv_export.mimetype,
            "mcp_tools": len(mcp_tools.json["result"]["tools"]),
        })
    finally:
        revoke_api_key(credential_id)
        set_setting("api_enabled", False)
        set_setting("mcp_enabled", False)


if __name__ == "__main__":
    main()
