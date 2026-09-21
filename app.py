# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import argparse
import csv
import io
import secrets
import sys
import threading
import webbrowser
from pathlib import Path

import psycopg
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, session, url_for

from statement_importer.config import ConfigError, save_settings, saved_connection_fields
from statement_importer.access import (
    create_api_key, list_api_keys, list_imports, revoke_api_key, search_transactions,
    service_status, set_setting,
)
from statement_importer.api import api
from statement_importer.database import (
    complete_import_batch,
    create_import_batch,
    dashboard_stats,
    ensure_fingerprint_schema,
    import_mapped_statement_atomic,
    import_statement_with_audit,
    record_import_file,
    provision_database,
    table_counts,
    test_connection,
)
from statement_importer.parsers import PasswordRequired, StatementError, parse_statement
from statement_importer.mapping import cleanup_pending, load_pending, mapped_rows, preview_pending, remove_pending, save_pending
from statement_importer.security import safe_csv_row
from statement_importer.maintenance import create_backup, create_reporting_user, list_backups


def resource_path(name: str) -> str:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(root / name)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
app.secret_key = secrets.token_bytes(32)
app.register_blueprint(api)


@app.before_request
def local_requests_only():
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        abort(403, "This application accepts local connections only")


@app.after_request
def security_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def verify_csrf() -> None:
    if not secrets.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "")):
        abort(400, "Invalid form token. Reload the page and try again.")


app.jinja_env.globals["csrf_token"] = csrf_token


def current_counts() -> dict[str, int] | None:
    try:
        return table_counts()
    except (ConfigError, psycopg.Error):
        return None


@app.get("/")
def index():
    cleanup_pending()
    counts = current_counts()
    if counts is None:
        return redirect(url_for("setup_database"))
    return render_template("index.html", results=None, counts=counts, stats=dashboard_stats())


@app.route("/setup", methods=["GET", "POST"])
def setup_database():
    fields = saved_connection_fields()
    error = None
    success = request.args.get("saved") == "1"
    if request.method == "POST":
        verify_csrf()
        settings = {
            "POSTGRES_HOST": request.form.get("host", "").strip(),
            "POSTGRES_PORT": request.form.get("port", "").strip(),
            "POSTGRES_DB": request.form.get("database", "").strip(),
            "POSTGRES_USER": request.form.get("user", "").strip(),
            "POSTGRES_PASSWORD": request.form.get("password", ""),
        }
        fields = settings
        try:
            if not all(settings.values()):
                raise ConfigError("Complete every connection field")
            int(settings["POSTGRES_PORT"])
            provision_database(settings)
            ensure_fingerprint_schema(settings)
            save_settings(settings)
            return redirect(url_for("setup_database", saved=1))
        except (ConfigError, ValueError, psycopg.Error) as exception:
            error = str(exception)
    return render_template("setup.html", fields=fields, error=error, success=success)


@app.post("/import")
def upload_statements():
    verify_csrf()
    default_password = request.form.get("password") or None
    files = [item for item in request.files.getlist("statements") if item.filename]
    results = []
    if not files:
        results.append({"status": "error", "file": "No file", "message": "Choose at least one statement."})
    batch_id = create_import_batch(len(files)) if files else None
    for index, uploaded in enumerate(files):
        password = request.form.get(f"password_{index}") or default_password
        suffix = Path(uploaded.filename).suffix.lower()
        if suffix not in {".xlsx", ".xls", ".csv"}:
            results.append({"status": "error", "file": uploaded.filename, "message": "Only .xlsx, .xls, and .csv files are accepted."})
            if batch_id:
                record_import_file(batch_id, results[-1])
            continue
        payload = uploaded.read()
        try:
            statement = parse_statement(payload, uploaded.filename, password)
            inserted, skipped = import_statement_with_audit(statement, batch_id)
            results.append(
                {
                    "status": "success", "file": uploaded.filename, "bank": statement.bank_name,
                    "bank_key": statement.bank_key, "table": statement.table_name,
                    "account": statement.account_number,
                    "account_masked": "*" * max(0, len(statement.account_number) - 4) + statement.account_number[-4:],
                    "period_start": statement.period_start, "period_end": statement.period_end,
                    "period": f"{statement.period_start.isoformat()} to {statement.period_end.isoformat()}",
                    "date_range": f"{statement.first_transaction_date.isoformat()} to {statement.last_transaction_date.isoformat()}",
                    "parsed": len(statement.rows), "inserted": inserted, "skipped": skipped,
                    "reconciliations": statement.reconciliations, "warnings": statement.warnings,
                    "audit_recorded": True,
                }
            )
        except PasswordRequired as error:
            results.append({"status": "error", "file": uploaded.filename, "message": str(error)})
        except StatementError as error:
            if "not recognized" in str(error).lower() or uploaded.filename.lower().endswith(".csv"):
                token = save_pending(payload, uploaded.filename)
                results.append({"status": "needs_mapping", "file": uploaded.filename,
                                "message": "Bank format needs mapping before import.",
                                "mapping_url": url_for("map_statement", token=token)})
            else:
                results.append({"status": "error", "file": uploaded.filename, "message": str(error)})
        except (ConfigError, psycopg.Error) as error:
            results.append({"status": "error", "file": uploaded.filename, "message": f"Database error: {error}"})
        except Exception as error:
            app.logger.exception("Statement import failed")
            results.append({"status": "error", "file": uploaded.filename, "message": f"Import failed: {error}"})
        if batch_id and not results[-1].get("audit_recorded"):
            record_import_file(batch_id, results[-1])
    if batch_id:
        complete_import_batch(batch_id, results)
    counts = current_counts()
    if counts is None:
        return redirect(url_for("setup_database"))
    return render_template("index.html", results=results, counts=counts, stats=dashboard_stats(), batch_id=batch_id)


@app.route("/map/<token>", methods=["GET", "POST"])
def map_statement(token: str):
    error = None
    preview = None
    success = None
    filename = "Statement"
    try:
        _, filename = load_pending(token)
        if request.method == "POST":
            verify_csrf()
            if request.form.get("action") == "import":
                mapped = mapped_rows(token, request.form.to_dict())
                bank_key, table_name, batch_id, inserted, skipped = import_mapped_statement_atomic(
                    mapped, request.form.get("profile_name") or "Default"
                )
                result = {"status": "success", "file": mapped["filename"], "bank_key": bank_key,
                          "account": mapped["account_number"], "period_start": mapped["period_start"],
                          "period_end": mapped["period_end"], "parsed": len(mapped["rows"]),
                          "inserted": inserted, "skipped": skipped,
                          "reconciliations": [f"Running balances reconcile across {len(mapped['rows'])} mapped transactions"]}
                remove_pending(token)
                success = {"bank": mapped["bank_name"], "table": table_name,
                           "inserted": inserted, "skipped": skipped}
            else:
                preview = preview_pending(token, request.form.get("password") or None)
        else:
            preview = preview_pending(token)
    except (StatementError, PasswordRequired, ValueError, psycopg.Error) as exception:
        error = str(exception)
    return render_template("mapping.html", token=token, filename=filename, preview=preview, error=error, success=success)


@app.route("/access", methods=["GET", "POST"])
def access_settings():
    generated_key = None
    if request.method == "POST":
        verify_csrf()
        action = request.form.get("action")
        if action == "toggle_api":
            set_setting("api_enabled", request.form.get("enabled") == "true")
        elif action == "toggle_mcp":
            set_setting("mcp_enabled", request.form.get("enabled") == "true")
        elif action == "create_key":
            generated_key = create_api_key(request.form.get("label", "Local integration"))
        elif action == "revoke_key":
            revoke_api_key(request.form.get("key_id", ""))
    return render_template(
        "access.html", services=service_status(), credentials=list_api_keys(), generated_key=generated_key,
        base_url=request.host_url.rstrip("/"),
    )


@app.route("/maintenance", methods=["GET", "POST"])
def maintenance():
    error = None
    backup_created = None
    reporting = None
    if request.method == "POST":
        verify_csrf()
        try:
            if request.form.get("action") == "backup":
                backup_created = create_backup().name
            elif request.form.get("action") == "reporting_user":
                reporting = create_reporting_user(
                    request.form.get("admin_user", ""), request.form.get("admin_password", "")
                )
            else:
                abort(400, "Unknown maintenance action")
        except (ConfigError, psycopg.Error, OSError, RuntimeError) as exception:
            error = str(exception)
    return render_template("maintenance.html", backups=list_backups(), error=error,
                           backup_created=backup_created, reporting=reporting)


@app.get("/transactions")
def transaction_browser():
    filters = request.args.to_dict()
    filters.setdefault("page_size", "100")
    rows, total = search_transactions(filters)
    return render_template("transactions.html", rows=rows, total=total, filters=filters)


@app.get("/imports")
def import_history():
    return render_template("imports.html", batches=list_imports(250))


@app.get("/export/transactions.csv")
def export_transactions_csv():
    filters = request.args.to_dict()
    filters["page"] = "1"
    filters["page_size"] = "500"
    rows, total = search_transactions(filters)
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(safe_csv_row(row) for row in rows)
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=statement-transactions.csv", "X-Total-Count": str(total)},
    )


@app.get("/health")
def health():
    counts = current_counts()
    if counts is None:
        return jsonify({"status": "setup_required"}), 503
    return jsonify({"status": "ok", "tables": counts})


def main():
    parser = argparse.ArgumentParser(description="Local bank statement import utility")
    parser.add_argument("--migrate-only", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        ensure_fingerprint_schema()
    except ConfigError:
        if args.migrate_only:
            raise
    if args.migrate_only:
        print(table_counts())
        return
    if args.open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
