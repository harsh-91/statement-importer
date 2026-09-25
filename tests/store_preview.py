# Created by Harsh Nair (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
"""Isolated, zero-data Store screenshot preview; never connects to a database."""
from __future__ import annotations

import sys
from pathlib import Path

from flask import render_template
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as web  # noqa: E402


def preview_home():
    return render_template(
        "index.html",
        results=None,
        counts={"unified_bank_transactions": 0},
        stats={"transactions": 0, "banks": 0, "accounts": 0, "last_import": None},
        update=None,
        app_version=web.__version__,
    )


web.app.view_functions["index"] = preview_home
server = make_server("127.0.0.1", 0, web.app, threaded=True)
print(server.server_port, flush=True)
server.serve_forever()
