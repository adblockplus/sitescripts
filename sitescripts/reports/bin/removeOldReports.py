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
from sitescripts.utils import setupStderr
from sitescripts.reports.utils import get_db, executeQuery, removeReport


def removeOldReports(days=30):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    executeQuery(cursor, 'SELECT guid FROM #PFX#reports WHERE ADDDATE(ctime, INTERVAL %s DAY) < NOW()', days)
    for report in cursor:
        removeReport(report['guid'])

if __name__ == '__main__':
    setupStderr()
    removeOldReports()
