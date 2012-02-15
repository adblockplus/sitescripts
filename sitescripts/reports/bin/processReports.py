# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb, hashlib, sys, os, re
from time import time
from email.utils import parseaddr
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.reports.utils import getReport, saveReport, get_db, executeQuery

def getReports():
  count = 1000
  offset = 0
  while True:
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    executeQuery(cursor,
                '''SELECT guid FROM #PFX#reports WHERE hasscreenshot > 0 LIMIT %s OFFSET %s''',
                (count, offset))
    rows = cursor.fetchall()
    cursor.close()
    if len(rows) == 0:
      break
    for row in rows:
      yield row
    offset += len(rows)

def processReports():
  for report in getReports():
    guid = report.get('guid', None)
    reportData = getReport(guid)
    saveReport(guid, reportData)

if __name__ == '__main__':
  setupStderr()
  processReports()
