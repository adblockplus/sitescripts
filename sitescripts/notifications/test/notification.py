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

import json
import mock
import unittest

import sitescripts.notifications.web.notification as notification

class TestNotification(unittest.TestCase):
  def setUp(self):
    self.load_notifications_patcher = mock.patch("sitescripts.notifications.web.notification.load_notifications")
    self.load_notifications_mock = self.load_notifications_patcher.start()

  def tearDown(self):
    self.load_notifications_patcher.stop()

  def test_no_group(self):
    self.load_notifications_mock.return_value = [{"id": "1"}]
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "1")
    self.assertFalse("-" in result["version"])

  def test_not_in_group(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000-a/0"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "1")
    self.assertRegexpMatches(result["version"], r"-a/0")

  def test_in_group(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000-a/1"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "a")
    self.assertRegexpMatches(result["version"], r"-a/1")

  def test_not_in_one_of_many_groups(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{}]
      },
      {
        "id": "b",
        "variants": [{}]
      },
      {
        "id": "c",
        "variants": [{}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000-a/0-b/0-c/0"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "1")
    self.assertRegexpMatches(result["version"], r"-a/0-b/0-c/0")

  def test_in_one_of_many_groups(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{}]
      },
      {
        "id": "b",
        "variants": [{}]
      },
      {
        "id": "c",
        "variants": [{}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000-a/0-b/1-c/0"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "b")
    self.assertRegexpMatches(result["version"], r"-a/0-b/1-c/0")

  def test_not_put_in_group(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{"sample": 0}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "1")
    self.assertRegexpMatches(result["version"], r"-a/0")

  def test_put_in_group(self):
    self.load_notifications_mock.return_value = [
      {"id": "1"},
      {
        "id": "a",
        "variants": [{"sample": 1}]
      }
    ]
    result = json.loads(notification.notification({
      "QUERY_STRING": "lastVersion=197001010000"
    }, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "a")
    self.assertRegexpMatches(result["version"], r"-a/1")

  def test_notification_variant_merged(self):
    self.load_notifications_mock.return_value = [
      {
        "id": "a",
        "title.en-GB": "default",
        "message.en-GB": "default",
        "message.de-DE": "vorgabe",
        "variants": [
          {
            "sample": 1,
            "message.en-GB": "variant"
          }
        ]
      }
    ]
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "a")
    self.assertEqual(result["notifications"][0]["title.en-GB"], "default")
    self.assertEqual(result["notifications"][0]["message.en-GB"], "variant")
    self.assertEqual(result["notifications"][0]["message.de-DE"], "vorgabe")
    self.assertFalse("variants" in result["notifications"][0])
    self.assertFalse("sample" in result["notifications"][0])

  def test_no_variant_no_notifications(self):
    self.load_notifications_mock.return_value = [
      {
        "id": "a",
        "variants": [{"sample": 0}]
      }
    ]
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 0)

  @mock.patch("random.random")
  def test_probability_distribution_single_group(self, random_call):
    self.load_notifications_mock.return_value = [
      {
        "id": "a",
        "variants": [
          {
            "sample": 0.5,
            "title.en-GB": "1"
          },
          {
            "sample": 0.25,
            "title.en-GB": "2"
          },
          {
            "sample": 0.25,
            "title.en-GB": "3"
          }
        ]
      }
    ]
    random_call.return_value = 0
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "1")
    self.assertRegexpMatches(result["version"], r"-a/1")
    random_call.return_value = 0.5
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "1")
    self.assertRegexpMatches(result["version"], r"-a/1")
    random_call.return_value = 0.51
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "2")
    self.assertRegexpMatches(result["version"], r"-a/2")
    random_call.return_value = 0.75
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "2")
    self.assertRegexpMatches(result["version"], r"-a/2")
    random_call.return_value = 0.751
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "3")
    self.assertRegexpMatches(result["version"], r"-a/3")
    random_call.return_value = 1
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["title.en-GB"], "3")
    self.assertRegexpMatches(result["version"], r"-a/3")

  @mock.patch("random.random")
  def test_probability_distribution_multiple_groups(self, random_call):
    self.load_notifications_mock.return_value = [
      {
        "id": "a",
        "variants": [
          {
            "sample": 0.25,
            "title.en-GB": "1"
          },
          {
            "sample": 0.25,
            "title.en-GB": "2"
          }
        ]
      },
      {
        "id": "b",
        "variants": [
          {
            "sample": 0.25,
            "title.en-GB": "1"
          },
          {
            "sample": 0.25,
            "title.en-GB": "2"
          }
        ]
      }
    ]
    random_call.return_value = 0
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "a")
    self.assertEqual(result["notifications"][0]["title.en-GB"], "1")
    self.assertRegexpMatches(result["version"], r"-a/1-b/0")
    random_call.return_value = 0.251
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "a")
    self.assertEqual(result["notifications"][0]["title.en-GB"], "2")
    self.assertRegexpMatches(result["version"], r"-a/2-b/0")
    random_call.return_value = 0.51
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "b")
    self.assertEqual(result["notifications"][0]["title.en-GB"], "1")
    self.assertRegexpMatches(result["version"], r"-a/0-b/1")
    random_call.return_value = 0.751
    result = json.loads(notification.notification({}, lambda *args: None))
    self.assertEqual(len(result["notifications"]), 1)
    self.assertEqual(result["notifications"][0]["id"], "b")
    self.assertEqual(result["notifications"][0]["title.en-GB"], "2")
    self.assertRegexpMatches(result["version"], r"-a/0-b/2")

  def test_invalid_last_version(self):
    self.load_notifications_mock.return_value = []
    notification.notification({"QUERY_STRING": "lastVersion="},
                              lambda *args: None)
    notification.notification({"QUERY_STRING": "lastVersion=-"},
                              lambda *args: None)
    notification.notification({"QUERY_STRING": "lastVersion=-/"},
                              lambda *args: None)
    notification.notification({"QUERY_STRING": "lastVersion=-//"},
                              lambda *args: None)

  def test_version_header_present(self):
    self.load_notifications_mock.return_value = [{"id": "1"}]
    response_header_map = {}
    def start_response(status, response_headers):
      for name, value in response_headers:
        response_header_map[name] = value
    result = json.loads(notification.notification({}, start_response))
    self.assertEqual(result["version"],
                     response_header_map["ABP-Notification-Version"])

if __name__ == '__main__':
  unittest.main()
