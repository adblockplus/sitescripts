# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import hashlib, hmac, base64, MySQLdb, os, re, marshal, subprocess
from sitescripts.utils import get_config, cached, get_template, sendMail

def getReportSubscriptions(guid):
  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  executeQuery(cursor,
              '''SELECT url, hasmatches FROM #PFX#sublists INNER JOIN
              #PFX#subscriptions ON (#PFX#sublists.list = #PFX#subscriptions.id)
              WHERE report = %s''',
              (guid))
  rows = cursor.fetchall()
  cursor.close()
  return rows

def getReports(startTime):
  count = 1000
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

def getReport(guid):
  cursor = get_db().cursor()
  executeQuery(cursor,
              '''SELECT dump FROM #PFX#reports WHERE guid = %s''',
              (guid))
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
    executeQuery(cursor,
                '''INSERT INTO #PFX#users (id, reports) VALUES (%s, 1) ON DUPLICATE KEY UPDATE reports = reports + 1''',
                (contact))
  executeQuery(cursor,
              '''INSERT INTO #PFX#reports (guid, type, ctime, site, comment, status, contact, hasscreenshot, knownissues, dump)
                 VALUES (%(guid)s, %(type)s, FROM_UNIXTIME(%(ctime)s), %(site)s, %(comment)s, %(status)s, %(contact)s,
                 %(hasscreenshot)s, %(knownissues)s, %(dump)s) ON DUPLICATE KEY
                 UPDATE type = %(type)s, site = %(site)s, comment = %(comment)s, status = %(status)s,
                 hasscreenshot = %(hasscreenshot)s, knownissues = %(knownissues)s, dump = %(dump)s''',
              {'guid': guid, 'type': reportData.get('type', None), 'ctime': reportData['time'], 'site': reportData.get('siteName', None),
               'comment': reportData.get('comment', None), 'status': reportData.get('status', None), 'contact': contact,
               'hasscreenshot': reportData.get('hasscreenshot', 0), 'knownissues': knownIssues, 'dump': dumpstr})
  if len(reportData['subscriptions']) > 0:
    for sn in reportData['subscriptions']:
      executeQuery(cursor,
                  '''SELECT id FROM #PFX#subscriptions WHERE url = %s''',
                  (sn['id']))
      id = cursor.fetchone()
      if id != None:
        filterMatch = lambda f: any(u == sn['id'] for u in f.get('subscriptions', []))
        hasMatches = any(filterMatch(f) for f in reportData.get('filters', []))
        executeQuery(cursor,
               '''INSERT IGNORE INTO #PFX#sublists (report, list, hasmatches) VALUES (%s, %s, %s)''',
               (guid, id[0], hasMatches))

  get_db().commit()

  reportData['guid'] = guid
  file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.html')
  dir = os.path.dirname(file)
  if not os.path.exists(dir):
    os.makedirs(dir)
  template = get_template(get_config().get('reports', 'webTemplate'))
  template.stream(reportData).dump(file, encoding='utf-8')

def removeReport(guid):
  cursor = get_db().cursor()
  executeQuery(cursor,
         '''DELETE FROM #PFX#reports WHERE guid = %s''',
         (guid))
  get_db().commit()
  file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.html')
  if os.path.isfile(file):
    os.remove(file)
  file = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.png')
  if os.path.isfile(file):
    os.remove(file)

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
  cursor.execute(query, args)
