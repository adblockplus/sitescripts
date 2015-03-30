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

import MySQLdb
import StringIO
import json
import sys
import unittest
from urllib import urlencode

from sitescripts.filterhits import db
from sitescripts.filterhits.web.query import query_handler
from sitescripts.filterhits.web.submit import submit as submit_handler

valid_data = """{
  "version": 1,
  "timeSincePush": 12345,
  "addonName": "adblockplus",
  "addonVersion": "2.3.4",
  "application": "firefox",
  "applicationVersion": "31",
  "platform": "gecko",
  "platformVersion": "31",
  "filters": {
    "||example.com^": {
      "firstParty": {
        "example.com": {"hits": 12, "latest": 1414817340948},
        "example.org": {"hits": 4, "latest": 1414859271125}
      },
      "thirdParty": {
        "example.com": {"hits": 5, "latest": 1414916268769}
      },
      "subscriptions": ["EasyList", "EasyList Germany+EasyList"]
    }
  }
}"""

class APITestCase(unittest.TestCase):
  def clear_rows(self):
    if self.db:
      db.write(self.db, (("DELETE FROM filters",),
                         ("DELETE FROM frequencies",)))

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

  def assertResponse(self, handler, expected_response, expected_result=None, expected_headers=None, **environ):
    def check_response(response, headers):
      self.assertEqual(response, expected_response)
      if not expected_headers is None:
        self.assertEqual(headers, expected_headers)

    if "body" in environ:
      environ["CONTENT_LENGTH"] = len(environ["body"])
      environ["wsgi.input"] = StringIO.StringIO(environ["body"])
      del environ["body"]

    if "get_params" in environ:
      environ["QUERY_STRING"] = urlencode(environ["get_params"])
      del environ["get_params"]

    environ["wsgi.errors"] = sys.stderr
    result = handler(environ, check_response)
    if not expected_result is None:
      self.assertEqual(json.loads("".join(result)), expected_result)

  def test_submit(self):
    self.assertEqual(len(db.query(self.db, "SELECT * FROM frequencies")), 0)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM filters")), 0)
    # Ensure missing or invalid JSON results in an error
    self.assertResponse(submit_handler, "400 Processing Error",
                        REQUEST_METHOD="POST", body="")
    self.assertResponse(submit_handler, "400 Processing Error",
                        REQUEST_METHOD="POST", body="Oops...")
    self.assertResponse(submit_handler, "400 Processing Error",
                        REQUEST_METHOD="POST", body="{123:]")
    self.assertResponse(submit_handler, "400 Processing Error",
                        REQUEST_METHOD="POST", body="1")
    self.assertEqual(len(db.query(self.db, "SELECT * FROM frequencies")), 0)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM filters")), 0)
    # Ensure even an empty object, or one with the wrong fields returns OK
    self.assertResponse(submit_handler, "200 OK",
                        REQUEST_METHOD="POST", body="{}")
    self.assertResponse(submit_handler, "200 OK",
                        REQUEST_METHOD="POST", body="{\"hello\": \"world\"}")
    self.assertEqual(len(db.query(self.db, "SELECT * FROM frequencies")), 0)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM filters")), 0)
    # Now some actually valid data
    self.assertResponse(submit_handler, "200 OK",
                        REQUEST_METHOD="POST", body=valid_data)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM frequencies")), 2)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM filters")), 1)
    # Now make sure apparently valid data with timestamps that cause geometrical
    # mean calculations to fail with MySQL errors return OK but don't change DB
    invalid_data = json.loads(valid_data)
    invalid_data["filters"]["||example.com^"]["firstParty"]["example.com"]["latest"] = 3
    invalid_data = json.dumps(invalid_data)
    self.assertResponse(submit_handler, "200 OK",
                        REQUEST_METHOD="POST", body=invalid_data)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM frequencies")), 2)
    self.assertEqual(len(db.query(self.db, "SELECT * FROM filters")), 1)

  def test_query(self):
    # Basic query with no data, should return OK
    self.assertResponse(query_handler, "200 OK", {"count": 0, "total": 0, "results": [], "echo": 0})
    # If echo parameter is passed and is integer it should be returned
    self.assertResponse(query_handler, "200 OK", {"count": 0, "total": 0, "results": [], "echo": 1337},
                        get_params={ "echo": 1337 })
    self.assertResponse(query_handler, "200 OK", {"count": 0, "total": 0, "results": [], "echo": 0},
                        get_params={ "echo": "naughty" })
    # Now let's submit some data so we can query it back out
    test_data = [json.loads(valid_data), json.loads(valid_data), json.loads(valid_data)]
    test_data[1]["filters"]["##Second-Filter|"] = test_data[1]["filters"].pop("||example.com^")
    test_data[2]["filters"]["##Third-Filter|"] = test_data[2]["filters"].pop("||example.com^")
    for data in test_data:
      self.assertResponse(submit_handler, "200 OK",
                          REQUEST_METHOD="POST", body=json.dumps(data))
    # Ordering parameters should be respected
    self.assertResponse(query_handler, "200 OK", {"count": 1, "total": 6,
                                                  "results": [{'domain': 'example.com',
                                                               'filter': '||example.com^',
                                                               'frequency': 0}], "echo": 0},
                        get_params={ "order_by": "filter", "order": "desc", "take": "1" })
    self.assertResponse(query_handler, "200 OK", {"count": 1, "total": 6,
                                                  "results": [{'domain': 'example.com',
                                                               'filter': '##Second-Filter|',
                                                               'frequency': 0}], "echo": 0},
                        get_params={ "order_by": "filter", "order": "asc", "take": "1" })
    # As should filtering parameters
    self.assertResponse(query_handler, "200 OK", {"count": 1, "total": 3,
                                                  "results": [{'domain': 'example.com',
                                                               'filter': '##Third-Filter|',
                                                               'frequency': 0}], "echo": 0},
                        get_params={ "domain": "example.com", "take": "1" })
    self.assertResponse(query_handler, "200 OK", {"count": 1, "total": 2,
                                                  "results": [{'domain': 'example.org',
                                                               'filter': '##Third-Filter|',
                                                               'frequency': 4}], "echo": 0},
                        get_params={ "filter": "Third", "take": 1 })
    self.assertResponse(query_handler, "200 OK", {"count": 1, "total": 1,
                                                  "results": [{'domain': 'example.com',
                                                               'filter': '##Third-Filter|',
                                                               'frequency': 0}], "echo": 0},
                        get_params={ "domain": "example.com", "filter": "Third", "take": "1" })
    # ... and pagination parameters
    self.maxDiff = None
    self.assertResponse(query_handler, "200 OK", {"count": 2, "total": 6,
                                                  "results": [{'domain': 'example.org',
                                                               'filter': '||example.com^',
                                                               'frequency': 4},
                                                              {'domain': 'example.org',
                                                               'filter': '##Second-Filter|',
                                                               'frequency': 4}], "echo": 0},
                        get_params={ "skip": "1", "take": "2" })
    self.assertResponse(query_handler, "200 OK", {"count": 2, "total": 6,
                                                  "results": [{'domain': 'example.org',
                                                               'filter': '##Second-Filter|',
                                                               'frequency': 4},
                                                              {'domain': 'example.com',
                                                               'filter': '##Third-Filter|',
                                                               'frequency': 0}], "echo": 0},
                        get_params={ "skip": "2", "take": "2" })

if __name__ == '__main__':
  unittest.main()
