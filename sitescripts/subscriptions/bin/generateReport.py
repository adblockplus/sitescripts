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

import sys
import os
import re
import codecs
from urlparse import parse_qs
from gzip import GzipFile
from sitescripts.utils import get_config, setupStderr, sendMail
from sitescripts.extensions.utils import compareVersions
import sitescripts.subscriptions.subscriptionParser as subscriptionParser


def countSubscriptionRequests(logPath, counts):
    regexp = re.compile(r'"GET \/getSubscription\?([^" ]*) ')
    f = GzipFile(logPath, 'rb')
    for line in f:
        matches = re.search(regexp, line)
        if matches:
            query = matches.group(1)
            params = parse_qs(query)
            if not 'version' in params or compareVersions(params['version'][0], '1.3.5') < 0:
                continue
            if not 'url' in params:
                continue
            url = params['url'][0]
            if re.match(r'^https?:[\x00-\x7F]+$', url):
                if not url in counts:
                    counts[url] = 1
                else:
                    counts[url] += 1
    f.close()


def processFile(data, counts):
    result = []

    for line in re.sub(r'\r', '', data).split('\n'):
        line = line.strip()

        if line == '' or line[0] == '[':
            result.append(line)
        else:
            count = 0
            if line in counts:
                count = counts[line]
                del counts[line]
            result.append('%5i %s' % (count, line))

    return result


def loadSubscriptions(counts):
    global interval

    subscriptions = subscriptionParser.readSubscriptions()

    knownURLs = {}
    for subscription in subscriptions.values():
        for title, url, complete in subscription.variants:
            knownURLs[url] = True

    redirectData, goneData = subscriptionParser.getFallbackData()
    redirects = processFile(redirectData, counts)
    gone = processFile(goneData, counts)

    unaccounted = filter(lambda url: counts[url] >= 10, counts.keys())
    unaccounted.sort(key=lambda url: counts[url], reverse=True)
    for i in range(0, len(unaccounted)):
        url = unaccounted[i]
        mark = ' [?]'
        if url in knownURLs:
            mark = ''
        unaccounted[i] = '%5i %s%s' % (counts[url], url, mark)

    return (redirects, gone, unaccounted)


if __name__ == '__main__':
    setupStderr()

    counts = {}
    for i in range(1, 15):
        logPath = os.path.join(get_config().get('logs', 'dataPath'), get_config().get('logs', 'fileName') % i)
        countSubscriptionRequests(logPath, counts)

    redirects, gone, unaccounted = loadSubscriptions(counts)

    sendMail(get_config().get('subscriptions', 'reportTemplate'), {
        'redirects': redirects,
        'gone': gone,
        'unaccounted': unaccounted,
    })
