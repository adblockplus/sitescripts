# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import hashlib, MySQLdb, os, re, marshal
from sitescripts.utils import get_config, cached, get_template, sendMail

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

def saveReport(guid, reportData):
  dumpstr = marshal.dumps(reportData)
  cursor = get_db().cursor()
  executeQuery(cursor,
              '''INSERT INTO #PFX#reports (guid, type, ctime, site, dump)
                 VALUES (%s, %s, FROM_UNIXTIME(%s), %s, %s) ON DUPLICATE KEY
                 UPDATE type = %s, site = %s, dump = %s''',
              (guid, reportData.get('type', None), reportData['time'], reportData.get('siteName', None),
               dumpstr, reportData.get('type', None), reportData.get('siteName', None), dumpstr))
  if len(reportData['subscriptions']) > 0:
    for sn in reportData['subscriptions']:
      executeQuery(cursor,
                  '''SELECT id FROM #PFX#subscriptions WHERE url = %s''',
                  (sn['id']))
      id = cursor.fetchone()
      if id != None:
        executeQuery(cursor,
               '''INSERT IGNORE INTO #PFX#sublists (report, list) VALUES (%s, %s)''',
               (guid, id[0]))

  get_db().commit()

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

def mailDigest(templateData):
  sendMail(get_config().get('reports', 'mailDigestTemplate'), templateData)

def sendUpdateNotification(templateData):
  sendMail(get_config().get('reports', 'notificationTemplate'), templateData)

def calculateReportSecret(guid):
  hash = hashlib.md5()
  hash.update(get_config().get('reports', 'secret'))
  hash.update(guid)
  return hash.hexdigest()

def getDigestId(email):
  hash = hashlib.md5()
  hash.update(email)
  return hash.hexdigest()

def getDigestPath(dir, email):
  return os.path.join(dir, getDigestId(email) + '.html')
  
def getDigestSecret(id, (year, week, weekday)):
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
