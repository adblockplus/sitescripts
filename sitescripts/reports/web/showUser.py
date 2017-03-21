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
from urlparse import parse_qs
from sitescripts.reports.utils import getUser, getReportsForUser
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.web import url_handler


@url_handler('/showUser')
def handleRequest(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    params = parse_qs(environ.get('QUERY_STRING', ''))

    id = params.get('id', [''])[0].lower()
    if not re.match(r'^[\da-f]{32}$', id):
        return showError('Invalid or missing ID', start_response)

    user = getUser(id)
    if user == None:
        return showError('User not found', start_response)

    user['reportlist'] = getReportsForUser(id)

    template = get_template(get_config().get('reports', 'showUserTemplate'))
    start_response('200 OK', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render(user).encode('utf-8')]


def showError(message, start_response):
    template = get_template(get_config().get('reports', 'errorTemplate'))
    start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
    return [template.render({'message': message}).encode('utf-8')]
