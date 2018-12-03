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

import hashlib
import hmac
import base64
import MySQLdb
import os
import re
import marshal
import subprocess
from sitescripts.utils import get_config, cached, get_template, anonymizeMail, sendMail


def getReportSubscriptions(guid):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    executeQuery(cursor,
                 '''SELECT url, hasmatches FROM #PFX#sublists INNER JOIN
              #PFX#subscriptions ON (#PFX#sublists.list = #PFX#subscriptions.id)
              WHERE report = %s''',
                 guid)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def getReports(startTime):
    count = 10000
    offset = 0
    while True:
        cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
        executeQuery(cursor,
                     '''SELECT guid, type, UNIX_TIMESTAMP(ctime) AS ctime, status, site, contact,
                comment, hasscreenshot, knownissues
                FROM #PFX#reports WHERE ctime >= FROM_UNIXTIME(%s) LIMIT %s OFFSET %s''',
                     (startTime, count, offset))
        rows = cursor.fetchall()
        cursor.close()
        if len(rows) == 0:
            break
        for row in rows:
            yield row
        offset += len(rows)


def getReportsForUser(contact):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    executeQuery(cursor,
                 '''SELECT guid, type, UNIX_TIMESTAMP(ctime) AS ctime, status, site, contact,
              comment, hasscreenshot, knownissues
              FROM #PFX#reports WHERE contact = %s ORDER BY ctime DESC LIMIT 100''',
                 contact)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def getReport(guid):
    cursor = get_db().cursor()
    executeQuery(cursor, 'SELECT dump FROM #PFX#reports WHERE guid = %s', guid)
    report = cursor.fetchone()
    if report == None:
        return None

    reportData = marshal.loads(report[0])
    return reportData


def saveReport(guid, reportData, isNew=False):
    cursor = get_db().cursor()
    screenshot = reportData.get('screenshot', None)
    if screenshot != None:
        reportData['hasscreenshot'] = 2 if reportData.get('screenshotEdited', False) else 1
        try:
            saveScreenshot(guid, screenshot)
        except (TypeError, UnicodeEncodeError):
            reportData['hasscreenshot'] = 0
        del reportData['screenshot']
    knownIssues = len(reportData.get('knownIssues', []))
    contact = getUserId(reportData.get('email', None)) if reportData.get('email', None) else None
    dumpstr = marshal.dumps(reportData)

    if contact != None and isNew:
        executeQuery(cursor, 'INSERT INTO #PFX#users (id, reports) VALUES (%s, 1) ON DUPLICATE KEY UPDATE reports = reports + 1', contact)
    executeQuery(cursor,
                 '''INSERT INTO #PFX#reports (guid, type, ctime, site, comment, status, contact, hasscreenshot, knownissues, dump)
                 VALUES (%(guid)s, %(type)s, FROM_UNIXTIME(%(ctime)s), %(site)s, %(comment)s, %(status)s, %(contact)s,
                 %(hasscreenshot)s, %(knownissues)s, _binary %(dump)s) ON DUPLICATE KEY
                 UPDATE type = %(type)s, site = %(site)s, comment = %(comment)s, status = %(status)s,
                 hasscreenshot = %(hasscreenshot)s, knownissues = %(knownissues)s, dump = _binary %(dump)s''',
                 {'guid': guid, 'type': reportData.get('type', None), 'ctime': reportData['time'], 'site': reportData.get('siteName', None),
                  'comment': reportData.get('comment', None), 'status': reportData.get('status', None), 'contact': contact,
                  'hasscreenshot': reportData.get('hasscreenshot', 0), 'knownissues': knownIssues, 'dump': dumpstr})
    if len(reportData['subscriptions']) > 0:
        for sn in reportData['subscriptions']:
            executeQuery(cursor, 'SELECT id FROM #PFX#subscriptions WHERE url = %s', sn['id'])
            id = cursor.fetchone()
            if id != None:
                def filterMatch(f):
                    return any(u == sn['id'] for u in f.get('subscriptions', []))
                hasMatches = any(filterMatch(f) for f in reportData.get('filters', []))
                executeQuery(cursor, 'INSERT IGNORE INTO #PFX#sublists (report, list, hasmatches) VALUES (%s, %s, %s)', (guid, id[0], hasMatches))

    get_db().commit()

    reportData['guid'] = guid
    if contact:
        # TODO: The mail anonymization should happen in the template, not here
        origEmail = reportData['email']
        email = reportData['email']
        email = re.sub(r' at ', r'@', email)
        email = re.sub(r' dot ', r'.', email)
        reportData['email'] = anonymizeMail(email)
        reportData['uid'] = contact

    file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.html')
    dir = os.path.dirname(file)
    if not os.path.exists(dir):
        os.makedirs(dir)
    template = get_template(get_config().get('reports', 'webTemplate'))
    template.stream(reportData).dump(file, encoding='utf-8')

    if contact:
        reportData['email'] = origEmail


def removeReport(guid):
    cursor = get_db().cursor()
    executeQuery(cursor, 'DELETE FROM #PFX#reports WHERE guid = %s', guid)
    get_db().commit()
    file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.html')
    if os.path.isfile(file):
        os.remove(file)
    file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.png')
    if os.path.isfile(file):
        os.remove(file)


def getUser(contact):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    executeQuery(cursor, 'SELECT reports, positive, negative FROM #PFX#users WHERE id = %s', contact)
    user = cursor.fetchone()
    return user


@cached(3600)
def getUserUsefulnessScore(contact):
    if contact == None:
        return 0

    cursor = get_db().cursor()
    # source from http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    executeQuery(cursor,
                 '''SELECT ((positive + 1.9208) / (positive + negative)
                        - 1.96 * SQRT((positive * negative) / (positive + negative) + 0.9604) / (positive + negative))
                        / (1 + 3.8416 / (positive + negative)) AS score FROM #PFX#users WHERE id = %s''',
                 contact)
    score = cursor.fetchone()
    if score == None:
        return 0

    if score[0] == None:  # no score yet
        return 0.3
    else:
        return 4 * score[0]


def updateUserUsefulness(contact, newusefulness, oldusefulness):
    new = int(newusefulness)
    old = int(oldusefulness)
    if new == old:
        return
    positive = 0
    negative = 0
    if old > 0:
        positive -= 1
    elif old < 0:
        negative -= 1
    if new > 0:
        positive += 1
    elif new < 0:
        negative += 1
    cursor = get_db().cursor()
    executeQuery(cursor, 'UPDATE #PFX#users SET negative = negative + %s, positive = positive + %s WHERE id = %s', (negative, positive, contact))
    get_db().commit()


def saveScreenshot(guid, screenshot):
    prefix = 'data:image/png;base64,'
    if not screenshot.startswith(prefix):
        raise TypeError('Screenshot is not a PNG image')
    data = base64.b64decode(screenshot[len(prefix):])
    file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.png')
    dir = os.path.dirname(file)
    if not os.path.exists(dir):
        os.makedirs(dir)
    f = open(file, 'wb')
    f.write(data)
    f.close()
    if get_config().has_option('reports', 'pngOptimizerPath'):
        cmd = get_config().get('reports', 'pngOptimizerPath').split()
        cmd.append(file)
        subprocess.call(cmd)


def mailDigest(templateData):
    sendMail(get_config().get('reports', 'mailDigestTemplate'), templateData)


def sendUpdateNotification(templateData):
    sendMail(get_config().get('reports', 'notificationTemplate'), templateData)


def calculateReportSecret(guid):
    return hmac.new(get_config().get('reports', 'secret'), guid).hexdigest()


def calculateReportSecret_compat(guid):
    hash = hashlib.md5()
    hash.update(get_config().get('reports', 'secret'))
    hash.update(guid)
    return hash.hexdigest()


def getUserId(email):
    return hmac.new(get_config().get('reports', 'secret'), email.encode('utf-8')).hexdigest()


def getDigestId(email):
    hash = hashlib.md5()
    hash.update(email.encode('utf-8'))
    return hash.hexdigest()


def getDigestPath(dir, email):
    return os.path.join(dir, getDigestId(email) + '.html')


def getDigestSecret(id, (year, week, weekday)):
    mac = hmac.new(get_config().get('reports', 'secret'), id)
    mac.update(str(year))
    mac.update(str(week))
    return mac.hexdigest()


def getDigestSecret_compat(id, (year, week, weekday)):
    hash = hashlib.md5()
    hash.update(get_config().get('reports', 'secret'))
    hash.update(id)
    hash.update(str(year))
    hash.update(str(week))
    return hash.hexdigest()


@cached(600)
def get_db():
    database = get_config().get('reports', 'database')
    dbuser = get_config().get('reports', 'dbuser')
    dbpasswd = get_config().get('reports', 'dbpassword')
    if os.name == 'nt':
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset='utf8', named_pipe=True)
    else:
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset='utf8')


def executeQuery(cursor, query, args=None):
    tablePrefix = get_config().get('reports', 'dbprefix')
    query = re.sub(r'#PFX#', tablePrefix, query)
    cursor.execute('SET NAMES utf8mb4')
    cursor.execute('SET CHARACTER SET utf8mb4')
    cursor.execute('SET character_set_connection=utf8mb4')
    cursor.execute(query, args)
