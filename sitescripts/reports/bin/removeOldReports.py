# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb
from sitescripts.utils import setupStderr
from sitescripts.reports.utils import get_db, executeQuery, removeReport

def removeOldReports(days=30):
  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  executeQuery(cursor,
         '''SELECT guid FROM #PFX#reports WHERE ADDDATE(ctime, INTERVAL %s DAY) < NOW()''',
         (days))
  reports = cursor.fetchall()
  for report in reports:
    removeReport(report['guid'])

if __name__ == '__main__':
  setupStderr()
  removeOldReports()
