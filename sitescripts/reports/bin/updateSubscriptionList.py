# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb
from sitescripts.utils import setupStderr
from sitescripts.reports.utils import get_db, executeQuery
import sitescripts.subscriptions.subscriptionParser as subscriptionParser

def updateSubscriptionList():
  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  executeQuery(cursor, '''SELECT id, url FROM #PFX#subscriptions''')
  dbsubs = cursor.fetchall()
  
  subids = {}
  
  for dbsub in dbsubs:
    subids[dbsub['url']] = dbsub['id']
      
  subscriptions = subscriptionParser.readSubscriptions()
  for subscription in subscriptions.values():
    for title, url, complete in subscription.variants:
      id = subids.get(url);
      if id == None:
        executeQuery(cursor,
               '''INSERT INTO #PFX#subscriptions (url) VALUES (%s)''',
               (url))
      else:
        del subids[url]
  
  for url in subids:
    executeQuery(cursor,
           '''DELETE FROM #PFX#subscriptions WHERE id = %s''',
           (subids[url]))
  get_db().commit()

if __name__ == '__main__':
  setupStderr()
  updateSubscriptionList()
