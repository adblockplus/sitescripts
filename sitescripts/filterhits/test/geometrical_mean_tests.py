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

from sitescripts.filterhits import db, geometrical_mean

test_data =  [{
  "filters": {
    "##.top-box-right-ad": {
      "firstParty": {
        "acxiom-online.com": { "hits": 6, "latest": 1414817340948 },
        "google.com": { "hits": 50, "latest": 1414849084678 },
        "yahoo.com": { "hits": 14, "latest": 1414859271125 },
        "doubleclick.net": { "hits": 26, "latest": 1414823430333 }
      },
      "thirdParty": {
        "demdex.net": { "hits": 36, "latest": 1414838712373 }
      }
    }
  }
}, {
  "filters": {
    "##.top-box-right-ad": {
      "thirdParty": {
        "adsymptotic.com": { "hits": 49, "latest": 1414953943015 },
        "amazon.com": { "hits": 2, "latest": 1414913563746 },
        "live.com": { "hits": 34, "latest": 1414916268769 },
        "google.com": { "hits": 21, "latest": 1414953920364 },
        "yahoo.com": { "hits": 27, "latest": 1414917270343 }
      }
    }
  }
}, {
  "filters": {
    "##.top-box-right-ad": {
      "firstParty": {
        "google.com": { "hits": 14, "latest": 1415008533089 },
        "adsymptotic.com": { "hits": 15, "latest": 1414994112862 }
      },
      "thirdParty": {
        "yahoo.com": { "hits": 43, "latest": 1415045194098 }
      }
    },
    "stevedeace.com##.topAddHolder": {
      "firstParty": {
        "mathtag.com": { "hits": 14, "latest": 1415032601175 },
        "amazonaws.com": { "hits": 18, "latest": 1414977342966 }
      }
    }
  }
}]

class GeometricalMeanTestCase(unittest.TestCase):
  longMessage = True
  maxDiff = None

  def geometrical(self, interval, new, new_timestamp, old, old_timestamp):
    delta_divby_interval = (new_timestamp - old_timestamp) / 1000 / float(interval)
    return long(round(old ** (1 - delta_divby_interval) * new ** delta_divby_interval))

  def clear_rows(self):
    if self.db:
      db.write(self.db, (("DELETE FROM frequencies",),
                         ("DELETE FROM filters",)))

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

  def test_calculations(self):
    if not self.db:
      raise unittest.SkipTest("Not connected to test DB.")

    interval = 86400

    # Tables should be empty to start with
    self.assertEqual(db.query(self.db, "SELECT * FROM filters"), ())
    self.assertEqual(db.query(self.db, "SELECT * FROM frequencies"), ())
    # First batch
    db.write(self.db, geometrical_mean.update(interval, test_data[0]))
    self.assertEqual(db.query(self.db, "SELECT * FROM filters"),
                     (("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"),
                       u"##.top-box-right-ad"),))
    self.assertEqual(
      db.query(self.db, "SELECT * FROM frequencies"),
      (("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"acxiom-online.com",
        6L, datetime.utcfromtimestamp(1414817340948 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"demdex.net",
        36L, datetime.utcfromtimestamp(1414838712373 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"doubleclick.net",
        26L, datetime.utcfromtimestamp(1414823430333 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"google.com",
        50L, datetime.utcfromtimestamp(1414849084678 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"yahoo.com",
        14L, datetime.utcfromtimestamp(1414859271125 / 1000))))
    # Second batch
    db.write(self.db, geometrical_mean.update(interval, test_data[1]))
    self.assertEqual(db.query(self.db, "SELECT * FROM filters"),
                     (("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"),
                       u"##.top-box-right-ad"),))
    self.assertEqual(
      db.query(self.db, "SELECT * FROM frequencies"),
      (("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"acxiom-online.com",
        6L, datetime.utcfromtimestamp(1414817340948 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"adsymptotic.com",
        49L, datetime.utcfromtimestamp(1414953943015 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"amazon.com",
        2L, datetime.utcfromtimestamp(1414913563746 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"demdex.net",
        36L, datetime.utcfromtimestamp(1414838712373 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"doubleclick.net",
        26L, datetime.utcfromtimestamp(1414823430333 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"google.com",
        self.geometrical(interval, 21, 1414953920364, 50, 1414849084678),
        datetime.utcfromtimestamp(1414953920364 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"live.com",
        34L, datetime.utcfromtimestamp(1414916268769 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"yahoo.com",
        self.geometrical(interval, 27, 1414917270343, 14, 1414859271125),
        datetime.utcfromtimestamp(1414917270343 / 1000))))
    # Third batch
    db.write(self.db, geometrical_mean.update(interval, test_data[2]))
    self.assertEqual(db.query(self.db, "SELECT * FROM filters"),
                     (("22de8d2ba8429eb170a0ece6ea7a426f7b22e574".decode("hex"),
                       u"stevedeace.com##.topAddHolder"),
                      ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"),
                       u"##.top-box-right-ad")))
    self.assertEqual(
      db.query(self.db, "SELECT * FROM frequencies"),
      (("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"acxiom-online.com",
        6L, datetime.utcfromtimestamp(1414817340948 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"adsymptotic.com",
        self.geometrical(interval, 15, 1414994112862, 49, 1414953943015),
        datetime.utcfromtimestamp(1414994112862 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"amazon.com",
        2L, datetime.utcfromtimestamp(1414913563746 / 1000)),
       ("22de8d2ba8429eb170a0ece6ea7a426f7b22e574".decode("hex"), u'amazonaws.com',
        18L, datetime.utcfromtimestamp(1414977342966 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"demdex.net",
        36L, datetime.utcfromtimestamp(1414838712373 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"doubleclick.net",
        26L, datetime.utcfromtimestamp(1414823430333 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"google.com",
        self.geometrical(interval, 14, 1415008533089,
                         self.geometrical(interval, 21, 1414953920364,
                                          50, 1414849084678),
                         1414953920364),
        datetime.utcfromtimestamp(1415008533089 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"live.com",
        34L, datetime.utcfromtimestamp(1414916268769 / 1000)),
       ("22de8d2ba8429eb170a0ece6ea7a426f7b22e574".decode("hex"), u'mathtag.com',
        14L, datetime.utcfromtimestamp(1415032601175 / 1000)),
       ("8c5ea548436c61f05536e205a29ada6204f603b0".decode("hex"), u"yahoo.com",
        self.geometrical(interval, 43, 1415045194098,
                         self.geometrical(interval, 27, 1414917270343,
                                          14, 1414859271125),
                         1414917270343),
        datetime.utcfromtimestamp(1415045194098 / 1000))))

if __name__ == '__main__':
  unittest.main()
