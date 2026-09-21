# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import csv
import io
import json
import hashlib
import threading
import time
from collections import defaultdict, deque
from decimal import InvalidOperation
from functools import wraps

from flask import Blueprint, Response, jsonify, request

from .access import (
    account_balances,
    list_accounts,
    list_banks,
    list_imports,
    schema_summary,
    search_transactions,
    service_status,
    verify_api_key,
)
from .security import safe_csv_row
from .version import __version__


api = Blueprint("api", __name__)
RATE_LIMIT = 120
RATE_WINDOW_SECONDS = 60
_rate_lock = threading.Lock()
_rate_windows: dict[str, deque[float]] = defaultdict(deque)


def _token() -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-API-Key")


def _within_rate_limit(token: str) -> bool:
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _rate_lock:
        window = _rate_windows[key]
        while window and now - window[0] >= RATE_WINDOW_SECONDS:
            window.popleft()
        if len(window) >= RATE_LIMIT:
            return False
        window.append(now)
        return True


def require_service(service: str):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            status = service_status()
            if not status.get(f"{service}_enabled"):
                return jsonify({"error": f"{service.upper()} service is disabled"}), 403
            token = _token()
            if not verify_api_key(token):
                return jsonify({"error": "A valid API key is required"}), 401
            if not _within_rate_limit(token):
                response = jsonify({"error": "Rate limit exceeded; try again in one minute"})
                response.headers["Retry-After"] = "60"
                return response, 429
            try:
                return function(*args, **kwargs)
            except (ValueError, TypeError, InvalidOperation) as error:
                return jsonify({"error": f"Invalid request: {error}"}), 400
        return wrapped
    return decorator


@api.get("/api/v1/health")
@require_service("api")
def api_health():
    return jsonify({"status": "ok", "service": "Statement Importer API", "version": __version__})


@api.get("/api/v1/banks")
@require_service("api")
def api_banks():
    return jsonify({"data": list_banks()})


@api.get("/api/v1/accounts")
@require_service("api")
def api_accounts():
    return jsonify({"data": list_accounts()})


@api.get("/api/v1/imports")
@require_service("api")
def api_imports():
    return jsonify({"data": list_imports(int(request.args.get("limit", 100)))})


@api.get("/api/v1/balances")
@require_service("api")
def api_balances():
    return jsonify({"data": account_balances()})


@api.get("/api/v1/schema")
@require_service("api")
def api_schema():
    return jsonify({"data": schema_summary()})


@api.get("/api/v1/transactions")
@require_service("api")
def api_transactions():
    rows, total = search_transactions(request.args.to_dict())
    if request.args.get("format") == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(safe_csv_row(row) for row in rows)
        return Response(
            output.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
    return jsonify({
        "data": rows, "total": total,
        "page": max(1, int(request.args.get("page", 1))),
        "page_size": min(500, max(1, int(request.args.get("page_size", 100)))),
    })


TOOLS = [
    {"name": "list_banks", "description": "List registered banks and their transaction tables", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_accounts", "description": "List masked bank accounts and transaction date ranges", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "search_transactions", "description": "Search normalized bank transactions", "inputSchema": {"type": "object", "properties": {
        "bank": {"type": "string"}, "account_last4": {"type": "string"},
        "date_from": {"type": "string"}, "date_to": {"type": "string"},
        "direction": {"type": "string", "enum": ["credit", "debit"]},
        "search": {"type": "string"}, "page": {"type": "integer"}, "page_size": {"type": "integer", "maximum": 500},
    }}},
    {"name": "get_account_balances", "description": "Return the latest recorded balance for each masked account", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_import_history", "description": "Return recent statement import batches", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "maximum": 500}}}},
    {"name": "get_transaction_schema", "description": "Describe bank transaction tables and the unified view", "inputSchema": {"type": "object", "properties": {}}},
]


def _mcp_result(value):
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "isError": False}


def _mcp_search(arguments):
    rows, total = search_transactions(arguments)
    return {"data": rows, "total": total}


@api.post("/mcp")
@require_service("mcp")
def mcp_endpoint():
    payload = request.get_json(silent=True) or {}
    if payload.get("jsonrpc") != "2.0" or not isinstance(payload.get("method"), str):
        return jsonify({"jsonrpc": "2.0", "id": payload.get("id"),
                        "error": {"code": -32600, "message": "Invalid JSON-RPC request"}}), 400
    method = payload.get("method")
    request_id = payload.get("id")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18", "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "statement-importer", "version": __version__},
        }
    elif method == "notifications/initialized":
        return "", 202
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = payload.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return jsonify({"jsonrpc": "2.0", "id": request_id,
                            "error": {"code": -32602, "message": "Tool arguments must be an object"}}), 400
        handlers = {
            "list_banks": lambda: list_banks(),
            "list_accounts": lambda: list_accounts(),
            "search_transactions": lambda: _mcp_search(arguments),
            "get_account_balances": lambda: account_balances(),
            "get_import_history": lambda: list_imports(int(arguments.get("limit", 100))),
            "get_transaction_schema": lambda: schema_summary(),
        }
        if name not in handlers:
            return jsonify({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Unknown tool"}})
        result = _mcp_result(handlers[name]())
    else:
        return jsonify({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}})
    return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})


@api.get("/api/v1/openapi.json")
def openapi_document():
    return jsonify({
        "openapi": "3.1.0", "info": {"title": "Statement Importer API", "version": __version__},
        "servers": [{"url": "/"}],
        "components": {"securitySchemes": {"ApiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}},
        "paths": {path: {"get": {"security": [{"ApiKey": []}], "responses": {"200": {"description": "Success"}}}} for path in [
            "/api/v1/health", "/api/v1/banks", "/api/v1/accounts", "/api/v1/transactions",
            "/api/v1/imports", "/api/v1/balances", "/api/v1/schema",
        ]},
    })
