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

import unittest

import MySQLdb

from sitescripts.filterhits.test import test_helpers
from sitescripts.filterhits import db

class DbTestCase(test_helpers.FilterhitsTestCase):
  longMessage = True
  maxDiff = None

  def test_query_and_write(self):
    insert_sql = """INSERT INTO `filters` (filter, sha1)
                    VALUES (%s, UNHEX(SHA1(filter)))"""
    select_sql = "SELECT filter FROM filters ORDER BY filter ASC"

    # Table should be empty to start with
    self.assertEqual(db.query(self.db, select_sql), ())
    # Write some data and query it back
    db.write(self.db, ((insert_sql, "something"),))
    self.assertEqual(db.query(self.db, select_sql), ((u"something",),))
    # Write an array of SQL strings
    db.write(self.db, ((insert_sql, "a"), (insert_sql, "b"), (insert_sql, "c")))
    self.assertEqual(db.query(self.db, select_sql), ((u"a",), (u"b",), (u"c",), (u"something",)))
    # Write a sequence of SQL but roll back when a problem arrises
    with self.assertRaises(MySQLdb.ProgrammingError):
      db.write(self.db, ((insert_sql, "f"), (insert_sql, "g"), (insert_sql, "h"),
                         ("GFDGks",)))
    self.assertEqual(db.query(self.db, select_sql), ((u"a",), (u"b",), (u"c",), (u"something",)))

if __name__ == "__main__":
  unittest.main()
