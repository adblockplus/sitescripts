# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2014 Eyeo GmbH
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

import sys, os, MySQLdb
from sitescripts.utils import get_config, setupStderr

"""
This script adds domains supplied on the command line to the "correct domains"
list permanently. This is useful for less popular domains that are commonly
affected by false positives.
"""

def forceDomains(domains):
  db = _get_db()
  for domain in domains:
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""INSERT INTO domains(domain, forceinclusion) VALUES (%s, 1)
                      ON DUPLICATE KEY UPDATE forceinclusion = 1""", domain)
  db.commit()

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

  if len(sys.argv) <= 1:
    print >>sys.stderr, "Please specify the domain names as command line parameters"
    sys.exit(1)

  forceDomains(sys.argv[1:])
