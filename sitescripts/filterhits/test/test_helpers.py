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

import tempfile
import shutil
import unittest

import MySQLdb

from sitescripts.filterhits import db
from sitescripts.utils import get_config

class FilterhitsTestCase(unittest.TestCase):
  config = get_config()
  _db = None
  _live_config = {
    "dbuser": config.get("filterhitstats", "dbuser"),
    "dbpassword": config.get("filterhitstats", "dbpassword"),
    "database": config.get("filterhitstats", "database"),
    "log_dir": config.get("filterhitstats", "log_dir")
  }
  _test_config = {
    "dbuser": config.get("filterhitstats", "test_dbuser"),
    "dbpassword": config.get("filterhitstats", "test_dbpassword"),
    "database": config.get("filterhitstats", "test_database")
  }

  def _clear_database(self):
    db.write(self._db, (("DELETE FROM frequencies",), ("DELETE FROM filters",)))

  @property
  def db(self):
    if (not self._db):
      self._db = db.connect()
      self._clear_database()
    return self._db

  def setUp(self):
    # Set up a temporary log directory for testing
    self.test_dir = tempfile.mkdtemp()
    # Set up test config
    for k, v in self._test_config.items():
      self.config.set("filterhitstats", k, v)
    self.config.set("filterhitstats", "log_dir", self.test_dir)

  def tearDown(self):
    # Clean the database and close our connection
    if self._db:
      self._clear_database()
      self._db.close()
      self._db = None
    # Clean any generated logs
    shutil.rmtree(self.test_dir, ignore_errors=True)
    # Restore the configuration
    for k, v in self._live_config.items():
      self.config.set("filterhitstats", k, v)
