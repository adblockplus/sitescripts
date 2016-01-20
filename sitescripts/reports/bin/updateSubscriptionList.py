# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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
from sitescripts.utils import setupStderr
from sitescripts.reports.utils import get_db, executeQuery
import sitescripts.subscriptions.subscriptionParser as subscriptionParser

def updateSubscriptionList():
  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  executeQuery(cursor, '''SELECT id, url FROM #PFX#subscriptions''')
  subids = {}
  for dbsub in cursor:
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
