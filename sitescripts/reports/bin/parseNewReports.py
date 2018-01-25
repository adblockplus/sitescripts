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

import os
import sys
import re
import marshal
import codecs
from urlparse import urlparse
from time import time
from xml.parsers.expat import ParserCreate, ExpatError, ErrorString
from sitescripts.utils import get_config, setupStderr
from sitescripts.reports.utils import saveReport, get_db, executeQuery
import sitescripts.subscriptions.knownIssuesParser as knownIssuesParser

reportData = None
tagStack = None

lengthRestrictions = {
    'default_string': 1024,
    'default_list': 512,
    'abp_version': 32,
    'abp_locale': 32,
    'app_name': 32,
    'app_vendor': 32,
    'app_version': 32,
    'platform_name': 32,
    'platform_version': 32,
    'platform_build': 32,
    'requests.type': 32,
    'requests.size': 32,
    'filters.hitCount': 16,
    'subscriptions.lastDownloadAttempt': 16,
    'subscriptions.lastDownloadSuccess': 16,
    'subscriptions.softExpiration': 16,
    'subscriptions.hardExpiration': 16,
    'subscriptions.downloadStatus': 32,
    'errors': 16,
    'errors.type': 16,
    'errors.line': 16,
    'errors.column': 16,
    'extensions.version': 32,
    'extensions.type': 32,
    'email': 256,
    'screenshot': 1024 * 1024,
}


def scanReports(dir):
    for file in os.listdir(dir):
        filePath = os.path.join(dir, file)
        if os.path.isfile(filePath) and file.endswith('.xml'):
            processReport(filePath)


def processReport(xmlFile):
    global reportData, tagStack

    guid = os.path.splitext(os.path.basename(xmlFile))[0]

    cursor = get_db().cursor()
    executeQuery(cursor, 'SELECT guid FROM #PFX#reports WHERE guid = %s', guid)
    report = cursor.fetchone()

    if report != None:
        os.remove(xmlFile)
        return

    source = open(xmlFile, 'rb')
    reportData = {'status': '', 'usefulness': 0, 'warnings': {}, 'requests': [], 'filters': [], 'subscriptions': [], 'extensions': [], 'errors': [], 'time': time()}
    tagStack = []

    parser = ParserCreate()
    parser.StartElementHandler = processElementStart
    parser.EndElementHandler = processElementEnd
    parser.CharacterDataHandler = processText
    try:
        parser.ParseFile(source)
    except ExpatError as error:
        reportData['warnings']['!parsing'] = 'Parsing error in the report: %s at line %i column %i' % (ErrorString(error.code), error.lineno, error.offset)

    source.seek(0)
    reportData['knownIssues'] = knownIssuesParser.findMatches(source, 'en-US')
    source.close()

    if 'screenshot' in reportData and not reportData['screenshot'].startswith('data:image/'):
        del reportData['screenshot']
    if 'email' in reportData and reportData['email'].find(' at ') < 0 and reportData['email'].find('@') < 0:
        del reportData['email']

    validateData(reportData)
    saveReport(guid, reportData, True)
    os.remove(xmlFile)


def processElementStart(name, attributes):
    global reportData, tagStack

    if name == 'report':
        reportData['type'] = attributes.get('type', 'unknown')
    elif name == 'adblock-plus':
        reportData['abp_version'] = attributes.get('version', 'unknown')
        if reportData['abp_version'] == '99.9':
            reportData['abp_version'] = 'development environment'
        reportData['abp_locale'] = attributes.get('locale', 'unknown')
    elif name == 'application':
        reportData['app_name'] = attributes.get('name', 'unknown')
        reportData['app_vendor'] = attributes.get('vendor', 'unknown')
        reportData['app_version'] = attributes.get('version', 'unknown')
        reportData['app_ua'] = attributes.get('userAgent', 'unknown')
    elif name == 'platform':
        reportData['platform_name'] = attributes.get('name', 'unknown')
        reportData['platform_version'] = attributes.get('version', 'unknown')
        reportData['platform_build'] = attributes.get('build', 'unknown')
    elif name == 'window':
        reportData['main_url'] = attributes.get('url', 'unknown')
        try:
            parsed = urlparse(reportData['main_url'])
            if parsed.netloc:
                reportData['siteName'] = parsed.netloc
            else:
                reportData['siteName'] = 'unknown'
        except:
            reportData['siteName'] = 'unknown'

        reportData['opener'] = attributes.get('opener', '')
        reportData['referrer'] = attributes.get('referrer', '')
    elif name == 'request':
        try:
            requestCount = int(attributes['count'])
        except:
            requestCount = 1
        reportData['requests'].append({
            'location': attributes.get('location', ''),
            'type': attributes.get('type', 'unknown'),
            'docDomain': attributes.get('docDomain', 'unknown'),
            'thirdParty': attributes.get('thirdParty', 'false') == 'true',
            'size': attributes.get('size', ''),
            'filter': attributes.get('filter', ''),
            'count': requestCount,
            'tagName': attributes.get('node', ''),
        })
    elif name == 'filter':
        reportData['filters'].append({
            'text': attributes.get('text', 'unknown'),
            'subscriptions': map(translateSubscriptionName, attributes.get('subscriptions', 'unknown').split(' ')),
            'hitCount': attributes.get('hitCount', 'unknown'),
        })
    elif name == 'subscription':
        reportData['subscriptions'].append({
            'id': attributes.get('id', 'unknown'),
            'disabledFilters': attributes.get('disabledFilters', 'unknown'),
            'version': attributes.get('version', 'unknown'),
            'lastDownloadAttempt': attributes.get('lastDownloadAttempt', 'unknown'),
            'lastDownloadSuccess': attributes.get('lastDownloadSuccess', 'unknown'),
            'softExpiration': attributes.get('softExpiration', 'unknown'),
            'hardExpiration': attributes.get('hardExpiration', 'unknown'),
            'downloadStatus': attributes.get('downloadStatus', 'unknown'),
        })
    elif name == 'extension':
        reportData['extensions'].append({
            'id': attributes.get('id', 'unknown'),
            'name': attributes.get('name', 'unknown'),
            'version': attributes.get('version', 'unknown'),
            'type': attributes.get('type', 'unknown'),
        })
    elif name == 'error':
        reportData['errors'].append({
            'type': attributes.get('type', 'unknown'),
            'text': attributes.get('text', 'unknown'),
            'file': attributes.get('file', 'unknown'),
            'line': attributes.get('line', 'unknown'),
            'column': attributes.get('column', 'unknown'),
            'sourceLine': re.sub(r'[\r\n]+$', '', attributes.get('sourceLine', '')),
        })
    elif name == 'screenshot':
        reportData['screenshotEdited'] = (attributes.get('edited', 'false') == 'true')

    tagStack.append([name, attributes])


def processElementEnd(name):
    global tagStack
    tagStack.pop()


def processText(text):
    if not len(tagStack):
        return

    [name, attributes] = tagStack[-1]
    if name == 'option':
        if attributes.get('id', None) == 'enabled':
            reportData['option_enabled'] = (text == 'true')
        if attributes.get('id', None) == 'objecttabs':
            reportData['option_objecttabs'] = (text == 'true')
        elif attributes.get('id', None) == 'collapse':
            reportData['option_collapse'] = (text == 'true')
        elif attributes.get('id', None) == 'privateBrowsing':
            reportData['option_privateBrowsing'] = (text == 'true')
        elif attributes.get('id', None) == 'subscriptionsAutoUpdate':
            reportData['option_subscriptionsAutoUpdate'] = (text == 'true')
        elif attributes.get('id', None) == 'javascript':
            reportData['option_javascript'] = (text == 'true')
        elif attributes.get('id', None) == 'cookieBehavior':
            try:
                reportData['option_cookieBehavior'] = int(text)
            except:
                pass
    elif name == 'screenshot':
        if 'screenshot' in reportData:
            reportData['screenshot'] += text
        else:
            reportData['screenshot'] = text
    elif name == 'comment':
        if 'comment' in reportData:
            reportData['comment'] += text
        else:
            reportData['comment'] = text
    elif name == 'email':
        if 'email' in reportData:
            reportData['email'] += text
        else:
            reportData['email'] = text


def translateSubscriptionName(name):
    if name == '~fl~':
        return 'My Ad Blocking Rules'
    elif name == '~wl~':
        return 'My Exception Rules'
    elif name == '~eh~':
        return 'My Element Hiding Rules'
    elif name == '~il~':
        return 'My Invalid Rules'
    elif name.startswith('~external~'):
        return 'External: ' + name[len('~external~'):len(name)]
    else:
        return name


def validateData(data, path=None):
    if path == 'warnings':
        return

    for key in data:
        if path is None:
            keyPath = key
        else:
            keyPath = path + '.' + key

        if isinstance(data[key], dict):
            validateData(data[key], keyPath)
        elif isinstance(data[key], list):
            limit = lengthRestrictions.get(keyPath, lengthRestrictions['default_list'])
            if len(data[key]) > limit:
                data[key] = data[key][0:limit]
                reportData['warnings'][keyPath] = 'List %s exceeded length limit and was truncated' % keyPath
            for i in range(len(data[key])):
                if isinstance(data[key][i], dict):
                    validateData(data[key][i], keyPath)
                elif isinstance(data[key][i], basestring):
                    itemPath = keyPath + '.item'
                    limit = lengthRestrictions.get(itemPath, lengthRestrictions['default_string'])
                    if len(data[key][i]) > limit:
                        data[key][i] = data[key][i][0:limit] + u'\u2026'
                        reportData['warnings'][itemPath] = 'Field %s exceeded length limit and was truncated' % itemPath
        elif isinstance(data[key], basestring):
            limit = lengthRestrictions.get(keyPath, lengthRestrictions['default_string'])
            if len(data[key]) > limit:
                data[key] = data[key][0:limit] + u'\u2026'
                reportData['warnings'][keyPath] = 'Field %s exceeded length limit and was truncated' % keyPath


if __name__ == '__main__':
    setupStderr()
    scanReports(get_config().get('reports', 'dataPath'))
