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

import MySQLdb
import os
import sys
import re
import marshal
from datetime import date
from time import time
from email.utils import parseaddr
from sitescripts.utils import get_config, setupStderr
from sitescripts.templateFilters import formatmime
from email.utils import formataddr
from sitescripts.reports.utils import mailDigest, getReports, getReportSubscriptions, calculateReportSecret, getDigestId, getDigestSecret, getUserUsefulnessScore
import sitescripts.subscriptions.subscriptionParser as subscriptionParser


def loadSubscriptions():
    global interval, weekDay

    subscriptions = subscriptionParser.readSubscriptions()

    results = {}
    resultList = []
    for subscription in subscriptions.values():
        if subscription.digest == 'daily' and interval == 'week':
            continue
        if subscription.digest == 'weekly' and interval == 'day':
            continue
        if interval == 'week' and subscription.digestDay != weekDay:
            continue

        for [title, url, complete] in subscription.variants:
            results[url] = subscription
        resultList.append(subscription)
    return (results, resultList)


def scanReports():
    global fakeSubscription, interval, subscriptions, startTime

    result = []

    for dbreport in getReports(startTime):
        matchSubscriptions = {}
        recipients = []
        reportSubscriptions = getReportSubscriptions(dbreport['guid'])
        if dbreport['type'] == 'false positive' or dbreport['type'] == 'false negative':
            for subscription in reportSubscriptions:
                subscriptionID = subscription.get('url', 'unknown')
                if subscriptionID in subscriptions:
                    if subscription.get('hasmatches', 0) > 0:
                        matchSubscriptions[subscriptionID] = subscriptions[subscriptionID]
                    # Send false negatives to all subscription authors, false positives
                    # only to subscriptions with matching filters
                    if dbreport['type'] == 'false negative' or subscription.get('hasmatches', 0) > 0:
                        recipients.append(subscriptions[subscriptionID])
        elif interval != 'week':
            # Send type "other" to fake subscription - daily reports
            recipients.append(fakeSubscription)
            subscriptionID = fakeSubscription.get('url', 'unknown')

        if len(recipients) == 0:
            continue

        report = {
            'url': get_config().get('reports', 'urlRoot') + dbreport['guid'] + '#secret=' + calculateReportSecret(dbreport['guid']),
            'weight': calculateReportWeight(dbreport, reportSubscriptions),
            'site': dbreport['site'],
            'subscriptions': recipients,
            'comment': re.sub(r'[\x00-\x20]', r' ', dbreport['comment']) if dbreport['comment'] != None else '',
            'type': dbreport['type'],
            'numSubscriptions': len(reportSubscriptions),
            'matchSubscriptions': matchSubscriptions.values(),
            'contact': dbreport['contact'],
            'hasscreenshot': dbreport['hasscreenshot'],
            'knownIssues': dbreport['knownissues'],
        }

        result.append(report)
    return result


def sendNotifications(reports):
    global subscriptionList

    for subscription in subscriptionList:
        selectedReports = filter(lambda report: subscription in report['subscriptions'], reports)
        if len(selectedReports) == 0:
            continue

        groups = {}
        for report in selectedReports:
            if report['site'] in groups:
                groups[report['site']]['reports'].append(report)
                groups[report['site']]['weight'] += report['weight']
            else:
                groups[report['site']] = {'name': report['site'], 'reports': [report], 'weight': report['weight'], 'dumpAll': False}

        miscGroup = {'name': 'Misc', 'reports': [], 'weight': None, 'dumpAll': True}
        for site, group in groups.items():
            if len(group['reports']) == 1:
                miscGroup['reports'].append(group['reports'][0])
                del groups[site]

        if len(miscGroup['reports']) > 0:
            groups[miscGroup['name']] = miscGroup

        groups = groups.values()
        groups.sort(lambda a, b: -cmp(a['weight'], b['weight']))
        for group in groups:
            group['reports'].sort(lambda a, b: -cmp(a['weight'], b['weight']))

        sendMail(subscription, groups)


def sendMail(subscription, groups):
    if hasattr(subscription, 'email'):
        email = subscription.email
    else:
        email = subscription['email']

    name, address = parseaddr(email)
    email = formatmime(formataddr((name, address)))

    id = getDigestId(address)
    digestLink = get_config().get('reports', 'urlRoot') + 'digest?id=%s&secret=%s' % (id, getDigestSecret(id, date.today().isocalendar()))

    mailDigest({'email': email, 'digestLink': digestLink, 'subscription': subscription, 'groups': groups})


def calculateReportWeight(report, subscriptions):
    global currentTime, startTime

    weight = 1.0
    if report['type'] == 'false positive' or report['type'] == 'false negative':
        weight /= len(subscriptions)
    if report['hasscreenshot'] == 1:
        weight += 0.7
    elif report['hasscreenshot'] == 2:
        weight += 0.3
    if report['knownissues'] > 0:
        weight -= 0.3
    if report['comment'] != None:
        if re.search(r'\btest\b', report['comment'], re.IGNORECASE):
            weight -= 0.5
        elif re.search(r'\S', report['comment']):
            weight += 0.5
    if report['contact'] != None:
        weight += getUserUsefulnessScore(report['contact'])

    weight += (report['ctime'] - startTime) / (currentTime - startTime) * 0.2
    return weight


if __name__ == '__main__':
    setupStderr()

    if len(sys.argv) < 2:
        raise Exception('No interval specified')

    interval = sys.argv[1]
    if interval not in ['all', 'week', 'day']:
        raise Exception('Invalid interval')

    if interval == 'week' and len(sys.argv) < 3:
        raise Exception('No weekday specified')
    weekDay = int(sys.argv[2]) if interval == 'week' else -1

    currentTime = time()
    startTime = 0
    if interval == 'week':
        startTime = currentTime - 7 * 24 * 60 * 60
    elif interval == 'day':
        startTime = currentTime - 24 * 60 * 60

    fakeSubscription = {'url': 'https://fake.adblockplus.org', 'name': get_config().get('reports', 'defaultSubscriptionName'), 'email': get_config().get('reports', 'defaultSubscriptionRecipient')}
    subscriptions, subscriptionList = loadSubscriptions()
    subscriptionList.append(fakeSubscription)
    reports = scanReports()
    sendNotifications(reports)
