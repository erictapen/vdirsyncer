
# -*- coding: utf-8 -*-
'''
    vdirsyncer.tests.storage.test_caldav
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Using an actual CalDAV server to test the CalDAV storage. Done by using
    Werkzeug's test client for WSGI apps. While this is pretty fast, Radicale
    has so much global state such that a clean separation of the unit tests is
    not guaranteed.

    :copyright: (c) 2014 Markus Unterwaditzer
    :license: MIT, see LICENSE for more details.
'''
__version__ = '0.1.0'

from unittest import TestCase
import tempfile
import shutil
import sys
import os

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse as WerkzeugResponse

from vdirsyncer.storage.caldav import CaldavStorage
from . import StorageTests


def do_the_radicale_dance(tmpdir):
    # All of radicale is already global state, the cleanliness of the code and
    # all hope is already lost. This function runs before every test.

    # This wipes out the radicale modules, to reset all of its state.
    for module in list(sys.modules):
        if module.startswith('radicale'):
            del sys.modules[module]

    # radicale.config looks for this envvar. We have to delete it before it
    # tries to load a config file.
    os.environ['RADICALE_CONFIG'] = ''
    import radicale.config

    # Now we can set some basic configuration.
    radicale.config.set('storage', 'type', 'filesystem')
    radicale.config.set('storage', 'filesystem_folder', tmpdir)
    radicale.config.set('rights', 'type', 'None')

    # This one is particularly useful with radicale's debugging logs and
    # pytest-capturelog, however, it is very verbose.
    #import radicale.log
    #radicale.log.start()


class Response(object):

    '''Fake API of requests module'''

    def __init__(self, x):
        self.x = x
        self.status_code = x.status_code
        self.content = x.get_data(as_text=False)
        self.headers = x.headers

    def raise_for_status(self):
        '''copied from requests itself'''
        if 400 <= self.status_code < 600:
            from requests.exceptions import HTTPError
            raise HTTPError(str(self.status_code))


class CaldavStorageTests(TestCase, StorageTests):
    tmpdir = None

    def _get_storage(self, **kwargs):
        self.tmpdir = tempfile.mkdtemp()

        do_the_radicale_dance(self.tmpdir)
        from radicale import Application
        app = Application()

        c = Client(app, WerkzeugResponse)
        server = 'http://127.0.0.1'
        calendar_path = '/bob/test.ics/'
        full_url = server + calendar_path

        def x(method, item, data=None, headers=None):
            assert '/' not in item
            url = calendar_path + item
            r = c.open(path=url, method=method, data=data, headers=headers)
            r = Response(r)
            return r
        return CaldavStorage(full_url, _request_func=x)

    def tearDown(self):
        self.app = None
        if self.tmpdir is not None:
            shutil.rmtree(self.tmpdir)
            self.tmpdir = None