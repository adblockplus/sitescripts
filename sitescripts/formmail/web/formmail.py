# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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
import datetime
from urlparse import parse_qsl
from sitescripts.utils import get_config, sendMail, setupStderr
from sitescripts.web import url_handler


@url_handler('/formmail')
def handleRequest(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
    if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
        return 'Unsupported request method'

    try:
        request_body_length = int(environ['CONTENT_LENGTH'])
    except:
        return 'Invalid or missing Content-Length header'

    request_body = environ['wsgi.input'].read(request_body_length)
    params = {}
    for key, value in parse_qsl(request_body):
        params[key] = value.decode('utf-8').strip()

    if not 'name' in params or params['name'] == '':
        return 'No name entered'
    if not 'email' in params or params['email'] == '':
        return 'No email address entered'
    if not 'subject' in params or params['subject'] == '':
        return 'No subject entered'
    if not 'message' in params or params['message'] == '':
        return 'No message entered'

    if not re.match(r'^\w[\w.+!-]+@\w[\w.-]+\.[a-zA-Z]{2,6}$', params['email']):
        return 'Invalid email address'

    params['time'] = datetime.datetime.now()
    sendMail(get_config().get('formmail', 'template'), params)
    return 'Message sent'
