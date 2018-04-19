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

import json
import mock
import unittest

import sitescripts.notifications.web.notification as notification


class TestNotification(unittest.TestCase):
    def setUp(self):
        self.load_notifications_patcher = mock.patch('sitescripts.notifications.web.notification.load_notifications')
        self.load_notifications_mock = self.load_notifications_patcher.start()

    def tearDown(self):
        self.load_notifications_patcher.stop()

    def test_no_group(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
        ]
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertFalse('-' in result['version'])

    def test_not_in_group(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_in_group(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/1',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'a')
        self.assertRegexpMatches(result['version'], r'-a/1')

    def test_not_in_one_of_many_groups(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
            {'id': 'b', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
            {'id': 'c', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0-b/0-c/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertRegexpMatches(result['version'], r'-a/0-b/0-c/0')

    def test_in_one_of_many_groups(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
            {'id': 'b', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
            {'id': 'c', 'variants': [
                {'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0-b/1-c/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'b')
        self.assertRegexpMatches(result['version'], r'-a/0-b/1-c/0')

    def test_not_put_in_group(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'sample': 0, 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_put_in_group(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': 'a', 'variants': [
                {'sample': 1, 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'a')
        self.assertRegexpMatches(result['version'], r'-a/1')

    def test_notification_variant_merged(self):
        self.load_notifications_mock.return_value = [
            {
                'id': 'a',
                'title': {'en-US': 'default'},
                'message': {'en-US': 'default'},
                'variants': [
                    {'sample': 1, 'message': {'en-US': 'variant'}},
                ],
            },
        ]
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'a')
        self.assertEqual(result['notifications'][0]['title']['en-US'], 'default')
        self.assertEqual(result['notifications'][0]['message']['en-US'], 'variant')
        self.assertFalse('variants' in result['notifications'][0])
        self.assertFalse('sample' in result['notifications'][0])

    def test_no_variant_no_notifications(self):
        self.load_notifications_mock.return_value = [
            {'id': 'a', 'variants': [{'sample': 0}]},
        ]
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 0)

    @mock.patch('random.random')
    def test_probability_distribution_single_group(self, random_call):
        self.load_notifications_mock.return_value = [
            {
                'id': 'a',
                'variants': [
                    {'sample': 0.5, 'title': {'en-US': '1'}, 'message': {'en-US': ''}},
                    {'sample': 0.25, 'title': {'en-US': '2'}, 'message': {'en-US': ''}},
                    {'sample': 0.25, 'title': {'en-US': '3'}, 'message': {'en-US': ''}},
                ],
            },
        ]
        random_call.return_value = 0
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '1')
        self.assertRegexpMatches(result['version'], r'-a/1')
        random_call.return_value = 0.5
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '1')
        self.assertRegexpMatches(result['version'], r'-a/1')
        random_call.return_value = 0.51
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '2')
        self.assertRegexpMatches(result['version'], r'-a/2')
        random_call.return_value = 0.75
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '2')
        self.assertRegexpMatches(result['version'], r'-a/2')
        random_call.return_value = 0.751
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '3')
        self.assertRegexpMatches(result['version'], r'-a/3')
        random_call.return_value = 1
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['title']['en-US'], '3')
        self.assertRegexpMatches(result['version'], r'-a/3')

    @mock.patch('random.random')
    def test_probability_distribution_multiple_groups(self, random_call):
        self.load_notifications_mock.return_value = [
            {
                'id': 'a',
                'variants': [
                    {'sample': 0.25, 'title': {'en-US': '1'}, 'message': {'en-US': ''}},
                    {'sample': 0.25, 'title': {'en-US': '2'}, 'message': {'en-US': ''}},
                ],
            },
            {
                'id': 'b',
                'variants': [
                    {'sample': 0.25, 'title': {'en-US': '1'}, 'message': {'en-US': ''}},
                    {'sample': 0.25, 'title': {'en-US': '2'}, 'message': {'en-US': ''}},
                ],
            },
        ]
        random_call.return_value = 0
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'a')
        self.assertEqual(result['notifications'][0]['title']['en-US'], '1')
        self.assertRegexpMatches(result['version'], r'-a/1-b/0')
        random_call.return_value = 0.251
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'a')
        self.assertEqual(result['notifications'][0]['title']['en-US'], '2')
        self.assertRegexpMatches(result['version'], r'-a/2-b/0')
        random_call.return_value = 0.51
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'b')
        self.assertEqual(result['notifications'][0]['title']['en-US'], '1')
        self.assertRegexpMatches(result['version'], r'-a/0-b/1')
        random_call.return_value = 0.751
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], 'b')
        self.assertEqual(result['notifications'][0]['title']['en-US'], '2')
        self.assertRegexpMatches(result['version'], r'-a/0-b/2')

    def test_invalid_last_version(self):
        self.load_notifications_mock.return_value = []
        notification.notification({'QUERY_STRING': 'lastVersion='},
                                  lambda *args: None)
        notification.notification({'QUERY_STRING': 'lastVersion=-'},
                                  lambda *args: None)
        notification.notification({'QUERY_STRING': 'lastVersion=-/'},
                                  lambda *args: None)
        notification.notification({'QUERY_STRING': 'lastVersion=-//'},
                                  lambda *args: None)

    def test_version_header_present(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
        ]
        response_header_map = {}

        def start_response(status, response_headers):
            for name, value in response_headers:
                response_header_map[name] = value
        result = json.loads(notification.notification({}, start_response))
        self.assertEqual(result['version'],
                         response_header_map['ABP-Notification-Version'])

    def test_default_group_notification_returned_if_valid(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {
                'id': 'a',
                'title': {'en-US': '0'},
                'message': {'en-US': '0'},
                'variants': [
                    {'title': {'en-US': '1'}, 'message': {'en-US': '1'}},
                ],
            },
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 2)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertEqual(result['notifications'][1]['id'], 'a')
        self.assertEqual(result['notifications'][1]['title']['en-US'], '0')
        self.assertNotIn('variants', result['notifications'][1])
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_default_group_notification_not_returned_if_invalid(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {
                'id': 'a',
                'title': {'en-US': '0'},
                'variants': [
                    {'title': {'en-US': '1'}, 'message': {'en-US': '1'}},
                ],
            },
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_invalid_notification_not_returned(self):
        self.load_notifications_mock.return_value = [
            {'id': '1', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
            {'id': '2', 'title': {'en-US': ''}, 'message': {}},
            {'id': '3', 'title': {}, 'message': {'en-US': ''}},
            {'id': '4', 'title': {}},
            {'id': '5', 'message': {}},
            {'id': '6'},
        ]
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertEqual(result['notifications'][0]['id'], '1')

    def test_stays_in_group_when_notification_present(self):
        self.load_notifications_mock.return_value = [
            {'id': 'a'},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0-b/1',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 0)
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_leaves_group_when_notification_absent(self):
        self.load_notifications_mock.return_value = []
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0-b/1',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 0)
        self.assertRegexpMatches(result['version'], r'[^-]*')

    def test_stays_in_group_when_notification_inactive(self):
        self.load_notifications_mock.return_value = [
            {'id': 'a', 'inactive': True},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/0-b/1',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 0)
        self.assertRegexpMatches(result['version'], r'-a/0')

    def test_stays_in_group_when_notification_inactive_assign_new_group(self):
        # See: https://issues.adblockplus.org/ticket/5827
        self.load_notifications_mock.return_value = [
            {'id': '1', 'inactive': True},
            {'id': '2', 'variants': [
                {'sample': 1, 'title': {'en-US': '2.1'}, 'message': {'en-US': '2.1'}},
            ]},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-1/0',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 1)
        self.assertRegexpMatches(result['version'], r'-1/0-2/1')

    def test_inactive_notifications_not_returned(self):
        self.load_notifications_mock.return_value = [
            {'id': 'a', 'title': {'en-US': ''}, 'message': {'en-US': ''}, 'inactive': True},
            {'id': 'b', 'title': {'en-US': ''}, 'message': {'en-US': ''}, 'inactive': False},
            {'id': 'c', 'title': {'en-US': ''}, 'message': {'en-US': ''}},
        ]
        result = json.loads(notification.notification({}, lambda *args: None))
        self.assertEqual(len(result['notifications']), 2)
        self.assertEqual(result['notifications'][0]['id'], 'b')
        self.assertEqual(result['notifications'][1]['id'], 'c')

    def test_inactive_notification_variant_not_returned(self):
        self.load_notifications_mock.return_value = [
            {'id': 'a', 'inactive': True},
        ]
        result = json.loads(notification.notification({
            'QUERY_STRING': 'lastVersion=197001010000-a/1',
        }, lambda *args: None))
        self.assertEqual(len(result['notifications']), 0)


if __name__ == '__main__':
    unittest.main()
