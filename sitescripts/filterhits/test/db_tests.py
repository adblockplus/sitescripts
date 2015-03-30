# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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
from datetime import datetime

from sitescripts.filterhits import db

class DbTestCase(unittest.TestCase):
  longMessage = True
  maxDiff = None

  def clear_rows(self):
    if self.db:
      db.write(self.db, (("DELETE FROM filters",),))

  def setUp(self):
    try:
      db.testing = True
      self.db = db.connect()
    except MySQLdb.Error:
      self.db = None
    self.clear_rows()

  def tearDown(self):
    if self.db:
      self.clear_rows()
      self.db.close()
      self.db = None

  def test_query_and_write(self):
    if not self.db:
      raise unittest.SkipTest("Not connected to test DB.")

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

if __name__ == '__main__':
  unittest.main()
