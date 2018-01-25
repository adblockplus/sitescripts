# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

import re
import os
import sys
from urlparse import parse_qs
from tempfile import mkstemp
from sitescripts.utils import get_config, setupStderr
from sitescripts.web import url_handler


@url_handler('/submitCrash')
def handleRequest(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    if not environ.get('HTTP_X_ADBLOCK_PLUS'):
        return showError('Please use Adblock Plus to submit crashes', start_response)

    if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('text/xml'):
        return showError('Unsupported request method', start_response)

    params = parse_qs(environ.get('QUERY_STRING', ''))

    requestVersion = params.get('version', ['0'])[0]
    if requestVersion != '1':
        return showError('Unsupported request version', start_response)

    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except ValueError:
        return showError('No content', start_response)

    dir = get_config().get('crashes', 'dataPath')
    if not os.path.exists(dir):
        os.makedirs(dir)

    filename = None
    try:
        fd, filename = mkstemp('.xml.tmp', 'crash_', dir)
        file = os.fdopen(fd, 'wb')
        file.write(environ['wsgi.input'].read(request_body_size))
        file.close()
        os.rename(filename, os.path.splitext(filename)[0])
    except Exception as e:
        if filename != None and os.path.isfile(filename):
            os.remove(filename)
        raise e

    start_response('200 Ok', [('Content-Type', 'text/plain; charset=utf-8')])
    return ['saved'.encode('utf-8')]


def showError(message, start_response):
    start_response('400 Processing Error', [('Content-Type', 'text/plain; charset=utf-8')])
    return [message.encode('utf-8')]
