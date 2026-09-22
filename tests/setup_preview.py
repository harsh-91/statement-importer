# Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
# Isolated UI fixture: never opens or modifies a real database.
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as web
from werkzeug.serving import make_server

attempts = 0
def provision(progress):
    global attempts
    attempts += 1
    progress('Checking PostgreSQL tools')
    time.sleep(2)
    progress('Preparing transaction tables')
    time.sleep(2)
    if attempts == 1:
        raise web.LocalPostgresError('Test database could not start. Review settings and retry.')

web.provision_managed_postgres = provision
web.saved_connection_fields = lambda: dict(POSTGRES_HOST='localhost', POSTGRES_PORT='5432',
                                          POSTGRES_DB='demo', POSTGRES_USER='demo')
web.app.view_functions['index'] = lambda: 'Ready to import'
server = make_server('127.0.0.1', 0, web.app, threaded=True)
print(server.server_port, flush=True)
server.serve_forever()
