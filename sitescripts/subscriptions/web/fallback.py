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

from time import time
from urlparse import urlparse, parse_qs
import sys
import os
import re
from sitescripts.utils import get_config, cached, setupStderr
from sitescripts.web import url_handler
import sitescripts.subscriptions.subscriptionParser as subscriptionParser


@url_handler('/getSubscription')
def handleSubscriptionFallbackRequest(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    redirects, gone = getData()

    start_response('200 OK', [('Content-Type', 'text/plain')])

    url = None
    params = parse_qs(environ.get('QUERY_STRING', ''))
    if 'url' in params:
        url = params['url'][0]

    if url and url in gone:
        return ['410']
    elif url and url in redirects:
        return ['301 %s' % redirects[url]]

    return []


@cached(600)
def getData():
    processed = set()

    redirectData, goneData = subscriptionParser.getFallbackData()
    redirects = processData(redirectData, processed, {})
    gone = processData(goneData, processed, set())

    return (redirects, gone)


def processData(data, processed, var):
    data = data.replace('\r', '')
    data = data.split('\n')

    currentTarget = None
    for line in data:
        line = line.strip()
        if line == '':
            continue

        match = re.match(r'^\[(.+)\]$', line)
        if match:
            currentTarget = match.group(1)
            urlData = urlparse(currentTarget)
            if urlData.scheme != 'http' and urlData.scheme != 'https':
                print >>sys.stderr, 'Redirect to a non-HTTP URL: %s' % currentTarget
            continue

        urlData = urlparse(line)
        if urlData.scheme != 'http' and urlData.scheme != 'https':
            print >>sys.stderr, 'Redirect for a non-HTTP URL: %s' % line

        if not isinstance(var, set) and not currentTarget:
            print >>sys.stderr, 'Redirect without a target: %s' % line
        if isinstance(var, set) and currentTarget:
            print >>sys.stderr, 'Gone entry with a target: %s' % line
        if line in processed:
            print >>sys.stderr, 'Multiple instructions for URL %s' % line

        if isinstance(var, set):
            var.add(line)
        else:
            var[line] = currentTarget

    return var
