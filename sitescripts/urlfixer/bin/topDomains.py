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

import sys
import os
import re
import math
import MySQLdb
from sitescripts.utils import get_config, setupStderr

"""
This script produces the list of top correct domain names currently in the
database.
"""

STATUS_TYPED = 1
STATUS_TYPO = 2
STATUS_CORRECTION = 3
STATUS_FALSE_POSITIVE = 4


def getTopDomains(count=5000):
    db = _get_db()
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, domain, forceinclusion FROM domains")

    domains = {}
    mandatory = []
    for result in cursor:
        domain = result["domain"]
        if "." not in domain or not re.search(r"[a-zA-Z]", domain):
            continue
        if re.search(r"['\"_,<>:;!$%&/()*+#~]|^\.|\.$|\.\.", domain):
            continue

        typed = _get_weighted_count(db, result["id"], STATUS_TYPED)
        correction = _get_weighted_count(db, result["id"], STATUS_CORRECTION)
        typo = _get_weighted_count(db, result["id"], STATUS_TYPO)
        fp = _get_weighted_count(db, result["id"], STATUS_FALSE_POSITIVE)
        correctness = _calculate_correctness(typed + correction, typo + fp)

        domains[domain] = correctness
        if result["forceinclusion"]:
            mandatory.append(domain)
    return sorted(domains.iterkeys(), key=lambda d: domains[d], reverse=True)[:count] + mandatory


def _get_weighted_count(db, domain, status):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT curr_month * 0.4 + prev_month * 0.3 +
                      curr_year * 0.2 + prev_year * 0.1 AS weighted_count
                    FROM corrections WHERE domain = %s AND status = %s""",
                   (domain, status))
    result = cursor.fetchone()
    if result == None:
        return 0
    else:
        return result["weighted_count"]


def _calculate_correctness(positive, negative):
    if positive + negative > 0:
        # Determine the correctness score with a confidence level of 0.95
        # (see http://www.evanmiller.org/how-not-to-sort-by-average-rating.html)
        fp = float(positive)
        fn = float(negative)
        total = fp + fn
        return ((fp + 1.9208) / total - 1.96 * math.sqrt((fp * fn) / total +
                                                         0.9604) / total) / (1 + 3.8416 / total)
    else:
        return 0


def _get_db():
    database = get_config().get("urlfixer", "database")
    dbuser = get_config().get("urlfixer", "dbuser")
    dbpasswd = get_config().get("urlfixer", "dbpassword")
    if os.name == "nt":
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset="utf8", named_pipe=True)
    else:
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset="utf8")

if __name__ == '__main__':
    setupStderr()

    domains = getTopDomains()
    for domain in domains:
        print domain.encode("utf-8")
