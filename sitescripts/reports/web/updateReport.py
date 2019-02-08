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
import random
from sitescripts.utils import get_config, get_template
from sitescripts.web import url_handler, form_handler
from sitescripts.reports.utils import (calculateReportSecret,
                                       calculateReportSecret_compat, getReport,
                                       saveReport, sendUpdateNotification,
                                       getUserId, updateUserUsefulness)

GUID_REGEX = r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$'


@url_handler('/updateReport')
@form_handler
def handleRequest(environ, start_response, params):
    guid = params.get('guid', '').lower()
    if not re.match(GUID_REGEX, guid):
        return showError('Invalid or missing report GUID', start_response)

    reportData = getReport(guid)

    if reportData is None:
        return showError('Report does not exist', start_response)

    secret = calculateReportSecret(guid)
    if (params.get('secret', '') != secret and
       params.get('secret', '') != calculateReportSecret_compat(guid)):
        return showError('Wrong secret value', start_response)

    reportData['status'] = params.get('status', '')
    if len(reportData['status']) > 1024:
        reportData['status'] = reportData['status'][:1024]

    oldusefulness = reportData.get('usefulness', '0')
    reportData['usefulness'] = params.get('usefulness', '0')

    if 'email' in reportData:
        updateUserUsefulness(getUserId(reportData['email']),
                             reportData['usefulness'], oldusefulness)

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
    start_response('400 Processing Error',
                   [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render({'message': message}).encode('utf-8')]
