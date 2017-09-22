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

import StringIO
import datetime
import tarfile
import unittest

import mock

import sitescripts.notifications.parser as parser


def _create_notification_archive(files):
    archive_stream = StringIO.StringIO()
    with tarfile.open(mode='w', fileobj=archive_stream) as archive:
        for name, text in files:
            file_stream = StringIO.StringIO(text)
            tar_info = tarfile.TarInfo(name)
            tar_info.size = len(file_stream.buf)
            archive.addfile(tar_info, file_stream)
    return archive_stream.getvalue()


def _format_time(time):
    return datetime.datetime.strftime(time, '%Y-%m-%dT%H:%M')


class TestParser(unittest.TestCase):
    def setUp(self):
        self.call_patcher = mock.patch('subprocess.call')
        self.call_patcher.start()
        self.check_output_patcher = mock.patch('subprocess.check_output')
        check_output_mock = self.check_output_patcher.start()

        def check_output_side_effect(command):
            if 'hg' in command and 'archive' in command:
                return _create_notification_archive(self.notification_to_load)
        check_output_mock.side_effect = check_output_side_effect

    def tearDown(self):
        self.call_patcher.stop()
        self.check_output_patcher.stop()

    def test_typical(self):
        self.notification_to_load = [('1', '''
severity = information
title.en-US = The title
message.en-US = The message
''')]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['id'], '1')
        self.assertEqual(notifications[0]['severity'], 'information')
        self.assertEqual(notifications[0]['title']['en-US'], 'The title')
        self.assertEqual(notifications[0]['message']['en-US'], 'The message')
        self.assertNotIn('inactive', notifications[0])

    def test_inactive(self):
        self.notification_to_load = [
            ('1', '\ninactive = Yes\n'),
            ('2', '\ninactive = No\n'),
        ]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 2)
        self.assertTrue(notifications[0]['inactive'])
        self.assertFalse(notifications[1]['inactive'])

    def test_in_range(self):
        current_time = datetime.datetime.now()
        hour_delta = datetime.timedelta(hours=1)
        start_time = current_time - hour_delta
        end_time = current_time + hour_delta
        self.notification_to_load = [('1', '''
start = %s
end = %s
''' % (_format_time(start_time), _format_time(end_time)))]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['id'], '1')
        self.assertNotIn('inactive', notifications[0])

    def test_after_range(self):
        current_time = datetime.datetime.now()
        start_time = current_time - datetime.timedelta(hours=2)
        end_time = current_time - datetime.timedelta(hours=1)
        self.notification_to_load = [('1', '''
start = %s
end = %s
''' % (_format_time(start_time), _format_time(end_time)))]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]['inactive'])

    def test_before_range(self):
        current_time = datetime.datetime.now()
        start_time = current_time + datetime.timedelta(hours=1)
        end_time = current_time + datetime.timedelta(hours=2)
        self.notification_to_load = [('1', '''
start = %s
end = %s
''' % (_format_time(start_time), _format_time(end_time)))]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]['inactive'])

    def test_start_and_end_not_present(self):
        current_time = datetime.datetime.now()
        hour_delta = datetime.timedelta(hours=1)
        start_time = current_time - hour_delta
        end_time = current_time + hour_delta
        self.notification_to_load = [('1', '''
start = %s
end = %s
''' % (_format_time(start_time), _format_time(end_time)))]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertNotIn('inactive', notifications[0])
        self.assertNotIn('start', notifications[0])
        self.assertNotIn('end', notifications[0])

    def test_interval(self):
        self.notification_to_load = [
            ('1', '\ninterval = 100\n'),
            ('2', '\ninterval = onehundred\n'),
        ]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['interval'], 100)

    def test_severity(self):
        self.notification_to_load = [
            ('1', '\nseverity = information\n'),
            ('2', '\nseverity = critical\n'),
            ('3', '\nseverity = normal\n'),
            ('4', '\nseverity = relentless\n'),
        ]
        notifications = parser.load_notifications()
        self.assertEqual(len(notifications), 4)
        self.assertEqual(notifications[0]['severity'], 'information')
        self.assertEqual(notifications[1]['severity'], 'critical')
        self.assertEqual(notifications[2]['severity'], 'normal')
        self.assertEqual(notifications[3]['severity'], 'relentless')

    def test_urls(self):
        self.notification_to_load = [
            ('1', '\nurls = adblockplus.org\n'),
            ('1', '\nurls = adblockplus.org eyeo.com\n'),
        ]
        notifications = parser.load_notifications()

        assert len(notifications) == 2
        assert notifications[0]['urlFilters'] == ['ADBLOCKPLUS.ORG^$document']
        assert notifications[1]['urlFilters'] == [
            'ADBLOCKPLUS.ORG^$document',
            'EYEO.COM^$document']

    def test_target(self):
        self.notification_to_load = [
            ('1', '\ntarget = extension=adblockplus\n'),
            ('2', '\ntarget = extensionVersion=1.2.3\n'),
            ('3', '\ntarget = extensionVersion>=1.2.3\n'),
            ('4', '\ntarget = extensionVersion<=1.2.3\n'),
            ('5', '\ntarget = application=chrome\n'),
            ('6', '\ntarget = applicationVersion=1.2.3\n'),
            ('7', '\ntarget = applicationVersion>=1.2.3\n'),
            ('8', '\ntarget = applicationVersion<=1.2.3\n'),
            ('9', '\ntarget = platform=chromium\n'),
            ('10', '\ntarget = platformVersion=1.2.3\n'),
            ('11', '\ntarget = platformVersion>=1.2.3\n'),
            ('12', '\ntarget = platformVersion<=1.2.3\n'),
            ('13', '\ntarget = blockedTotal=10\n'),
            ('14', '\ntarget = blockedTotal>=10\n'),
            ('15', '\ntarget = blockedTotal<=10\n'),
            ('16', '\ntarget = locales=en-US\n'),
            ('17', '\ntarget = locales=en-US,de-DE\n'),
        ]

        notifications = parser.load_notifications()

        assert len(notifications) == 17
        assert notifications[0]['targets'] == [{'extension': 'adblockplus'}]
        assert notifications[1]['targets'] == [{
            'extensionMinVersion': '1.2.3',
            'extensionMaxVersion': '1.2.3'}]
        assert notifications[2]['targets'] == [
            {'extensionMinVersion': '1.2.3'}]
        assert notifications[3]['targets'] == [{
            'extensionMaxVersion': '1.2.3'}]
        assert notifications[4]['targets'] == [{'application': 'chrome'}]
        assert notifications[5]['targets'] == [{
            'applicationMinVersion': '1.2.3',
            'applicationMaxVersion': '1.2.3'}]
        assert notifications[6]['targets'] == [{
            'applicationMinVersion': '1.2.3'}]
        assert notifications[7]['targets'] == [{
            'applicationMaxVersion': '1.2.3'}]
        assert notifications[8]['targets'] == [{'platform': 'chromium'}]
        assert notifications[9]['targets'] == [{
            'platformMinVersion': '1.2.3',
            'platformMaxVersion': '1.2.3'}]
        assert notifications[10]['targets'] == [{
            'platformMinVersion': '1.2.3'}]
        assert notifications[11]['targets'] == [{
            'platformMaxVersion': '1.2.3'}]
        assert notifications[12]['targets'] == [{
            'blockedTotalMin': 10,
            'blockedTotalMax': 10}]
        assert notifications[13]['targets'] == [{'blockedTotalMin': 10}]
        assert notifications[14]['targets'] == [{'blockedTotalMax': 10}]
        assert notifications[15]['targets'] == [{'locales': ['en-US']}]
        assert notifications[16]['targets'] == [{
            'locales': ['en-US', 'de-DE']}]


if __name__ == '__main__':
    unittest.main()
