# Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
import threading
import unittest
from unittest.mock import patch
import app as web


class SetupProgressTests(unittest.TestCase):
    def client(self, token):
        client = web.app.test_client()
        with client.session_transaction() as session:
            session['csrf_token'] = token
        return client

    def test_progress_is_live_session_scoped_and_duplicate_setup_blocked(self):
        owner, poller, other = [self.client(token) for token in ('owner', 'owner', 'other')]
        running, release = threading.Event(), threading.Event()
        responses = []
        def provision(progress):
            progress('Creating storage')
            running.set()
            release.wait(5)
        def post():
            responses.append(owner.post('/setup', data={'csrf_token': 'owner', 'mode': 'automatic'},
                             headers={'X-Setup-Request': '1'}))
        with patch.object(web, 'provision_managed_postgres', side_effect=provision):
            worker = threading.Thread(target=post)
            worker.start()
            try:
                self.assertTrue(running.wait(3))
                self.assertEqual(poller.get('/setup/progress').json['message'], 'Creating storage')
                self.assertTrue(poller.get('/setup/progress').json['running'])
                self.assertNotEqual(other.get('/setup/progress').json['message'], 'Creating storage')
                duplicate = other.post('/setup', data={'csrf_token': 'other', 'mode': 'automatic'},
                                       headers={'X-Setup-Request': '1'})
                self.assertEqual(duplicate.status_code, 409)
            finally:
                release.set()
                worker.join(5)
        self.assertEqual(responses[0].json['next'], '/')
        self.assertFalse(poller.get('/setup/progress').json['running'])

    def test_failure_releases_setup_lock_and_allows_retry(self):
        client = self.client('test')
        with patch.object(web, 'provision_managed_postgres', side_effect=web.LocalPostgresError('Tools missing')):
            response = client.post('/setup', data={'csrf_token': 'test', 'mode': 'automatic'},
                                   headers={'X-Setup-Request': '1'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], 'Tools missing')
        self.assertFalse(web.setup_lock.locked())
        self.assertFalse(client.get('/setup/progress').json['running'])
