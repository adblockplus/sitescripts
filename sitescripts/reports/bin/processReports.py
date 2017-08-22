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
import hashlib
import sys
import os
import re
from time import time
from email.utils import parseaddr
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.reports.utils import getReport, saveReport, get_db, executeQuery


def getReports():
    count = 1000
    offset = 0
    while True:
        cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
        executeQuery(cursor, 'SELECT guid FROM #PFX#reports WHERE hasscreenshot > 0 LIMIT %s OFFSET %s', (count, offset))
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
        if 'screenshot' in reportData:
            saveReport(guid, reportData)

if __name__ == '__main__':
    setupStderr()
    processReports()
