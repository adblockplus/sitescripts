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
import os
import sys
from urlparse import parse_qs
from sitescripts.utils import get_config, get_template
from sitescripts.web import url_handler
import sitescripts.subscriptions.knownIssuesParser as knownIssuesParser


@url_handler('/submitReport')
def handleRequest(environ, start_response):
    if not environ.get('HTTP_X_ADBLOCK_PLUS'):
        return showError('Please use Adblock Plus to submit reports', start_response)

    if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('text/xml'):
        return showError('Unsupported request method', start_response)

    params = parse_qs(environ.get('QUERY_STRING', ''))

    requestVersion = params.get('version', ['0'])[0]
    if requestVersion != '1':
        return showError('Unsupported request version', start_response)

    guid = params.get('guid', [''])[0].lower()
    if not re.match(r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$', guid):
        return showError('Invalid or missing GUID', start_response)

    path = os.path.join(get_config().get('reports', 'dataPath'), guid + '.xml')
    if os.path.exists(path) or os.path.exists(path + '.tmp'):
        return showError('Duplicate GUID', start_response)

    try:
        request_size = int(environ['CONTENT_LENGTH'])
    except (KeyError, ValueError):
        return showError('Invalid or missing Content-Length header', start_response,
                         '411 Length Required')

    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    try:
        file = open(path + '.tmp', 'wb')
        data = environ['wsgi.input'].read(request_size)
        file.write(data)
        file.close()

        knownIssues = knownIssuesParser.findMatches(data.splitlines(), params.get('lang', ['en-US'])[0])

        os.rename(path + '.tmp', path)
    except Exception as e:
        if os.path.isfile(path + '.tmp'):
            os.remove(path + '.tmp')
        raise e

    template = get_template(get_config().get('reports', 'submitResponseTemplate'))
    start_response('200 OK', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render({'url': get_config().get('reports', 'urlRoot') + guid, 'knownIssues': knownIssues}).encode('utf-8')]


def showError(message, start_response, response_code='400 Processing Error'):
    template = get_template(get_config().get('reports', 'errorTemplate'))
    start_response(response_code, [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render({'message': message}).encode('utf-8')]
