# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2017 eyeo GmbH
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
import random
from urlparse import parse_qsl
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.web import url_handler
from sitescripts.reports.utils import calculateReportSecret, calculateReportSecret_compat, getReport, saveReport, sendUpdateNotification, getUserId, updateUserUsefulness


@url_handler('/updateReport')
def handleRequest(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
        return showError('Unsupported request method', start_response)

    try:
        request_body_length = int(environ['CONTENT_LENGTH'])
    except:
        return showError('Invalid or missing Content-Length header', start_response)

    request_body = environ['wsgi.input'].read(request_body_length)
    params = {}
    for key, value in parse_qsl(request_body):
        params[key] = value.decode('utf-8')

    guid = params.get('guid', '').lower()
    if not re.match(r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$', guid):
        return showError('Invalid or missing report GUID', start_response)

    reportData = getReport(guid)

    if reportData == None:
        return showError('Report does not exist', start_response)

    secret = calculateReportSecret(guid)
    if params.get('secret', '') != secret and params.get('secret', '') != calculateReportSecret_compat(guid):
        return showError('Wrong secret value', start_response)

    reportData['status'] = params.get('status', '')
    if len(reportData['status']) > 1024:
        reportData['status'] = reportData['status'][:1024]

    oldusefulness = reportData.get('usefulness', '0')
    reportData['usefulness'] = params.get('usefulness', '0')
    if 'email' in reportData:
        updateUserUsefulness(getUserId(reportData['email']), reportData['usefulness'], oldusefulness)

    saveReport(guid, reportData)

    if params.get('notify', '') and 'email' in reportData:
        email = reportData['email']
        email = re.sub(r' at ', r'@', email)
        email = re.sub(r' dot ', r'.', email)
        if re.match(r'^[\w.%+-]+@[\w.%+-]+(\.[\w.%+-]+)+', email):
            sendUpdateNotification({
                'email': email,
                'url': get_config().get('reports', 'urlRoot') + guid,
                'status': reportData['status'],
            })

    newURL = get_config().get('reports', 'urlRoot') + guid
    newURL += '?updated=' + str(int(random.uniform(0, 10000)))
    newURL += '#secret=' + secret
    start_response('302 Found', [('Location', newURL.encode('utf-8'))])
    return []


def showError(message, start_response):
    template = get_template(get_config().get('reports', 'errorTemplate'))
    start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render({'message': message}).encode('utf-8')]
