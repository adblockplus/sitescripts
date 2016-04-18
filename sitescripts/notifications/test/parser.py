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

import StringIO
import datetime
import tarfile
import unittest

import mock

import sitescripts.notifications.parser as parser


def _create_notification_archive(name, text):
    archive_stream = StringIO.StringIO()
    file_stream = StringIO.StringIO(text)
    tar_info = tarfile.TarInfo(name)
    tar_info.size = len(file_stream.buf)
    with tarfile.open(mode="w", fileobj=archive_stream) as archive:
        archive.addfile(tar_info, file_stream)
    return archive_stream.getvalue()


def _format_time(time):
    return datetime.datetime.strftime(time, "%Y-%m-%dT%H:%M")


class TestParser(unittest.TestCase):
    def setUp(self):
        self.call_patcher = mock.patch("subprocess.call")
        self.call_patcher.start()
        self.check_output_patcher = mock.patch("subprocess.check_output")
        check_output_mock = self.check_output_patcher.start()

        def check_output_side_effect(command):
            if "hg" in command and "archive" in command:
                return _create_notification_archive(*self.notification_to_load)
        check_output_mock.side_effect = check_output_side_effect

    def tearDown(self):
        self.call_patcher.stop()
        self.check_output_patcher.stop()

    def test_typical(self):
        self.notification_to_load = ("1", """
severity = information
title.en-US = The title
message.en-US = The message
""")
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], "1")
        self.assertEqual(notifications[0]["severity"], "information")
        self.assertEqual(notifications[0]["title"]["en-US"], "The title")
        self.assertEqual(notifications[0]["message"]["en-US"], "The message")
        self.assertNotIn("inactive", notifications[0])

    def test_inactive(self):
        self.notification_to_load = ("1", """
inactive = Yes
""")
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["inactive"])
        self.notification_to_load = ("1", """
inactive = No
""")
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertFalse(notifications[0]["inactive"])

    def test_in_range(self):
        current_time = datetime.datetime.now()
        hour_delta = datetime.timedelta(hours=1)
        start_time = current_time - hour_delta
        end_time = current_time + hour_delta
        self.notification_to_load = ("1", """
start = %s
end = %s
""" % (_format_time(start_time), _format_time(end_time)))
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], "1")
        self.assertNotIn("inactive", notifications[0])

    def test_after_range(self):
        current_time = datetime.datetime.now()
        start_time = current_time - datetime.timedelta(hours=2)
        end_time = current_time - datetime.timedelta(hours=1)
        self.notification_to_load = ("1", """
start = %s
end = %s
""" % (_format_time(start_time), _format_time(end_time)))
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["inactive"])

    def test_before_range(self):
        current_time = datetime.datetime.now()
        start_time = current_time + datetime.timedelta(hours=1)
        end_time = current_time + datetime.timedelta(hours=2)
        self.notification_to_load = ("1", """
start = %s
end = %s
""" % (_format_time(start_time), _format_time(end_time)))
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["inactive"])

    def test_start_and_end_not_present(self):
        current_time = datetime.datetime.now()
        hour_delta = datetime.timedelta(hours=1)
        start_time = current_time - hour_delta
        end_time = current_time + hour_delta
        self.notification_to_load = ("1", """
start = %s
end = %s
""" % (_format_time(start_time), _format_time(end_time)))
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertNotIn("inactive", notifications[0])
        self.assertNotIn("start", notifications[0])
        self.assertNotIn("end", notifications[0])

if __name__ == "__main__":
    unittest.main()
