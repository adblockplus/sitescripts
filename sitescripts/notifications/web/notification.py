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

import copy
import json
import random
import time
import urlparse

from sitescripts.notifications.parser import load_notifications
from sitescripts.web import url_handler


def _determine_groups(version, notifications):
    version_groups = dict(x.split('/') for x in version.split('-')[1:]
                          if x.count('/') == 1)
    groups = []
    for notification in notifications:
        group_id = notification['id']
        if group_id in version_groups:
            groups.append({'id': group_id, 'variant': int(version_groups[group_id])})
    return groups


def _assign_groups(groups, notifications):
    selection = random.random()
    start = 0
    for notification in notifications:
        if 'variants' not in notification:
            continue
        if notification['id'] in [g['id'] for g in groups]:
            continue
        group = {'id': notification['id'], 'variant': 0}
        groups.append(group)
        for i, variant in enumerate(notification['variants']):
            sample_size = variant['sample']
            end = start + sample_size
            selected = sample_size > 0 and start <= selection <= end
            start = end
            if selected:
                group['variant'] = i + 1
                break


def _get_active_variant(notifications, groups):
    for group in groups:
        group_id = group['id']
        variant = group['variant']
        if variant == 0:
            continue
        notification = next((x for x in notifications if x['id'] == group_id), None)
        if not notification:
            continue
        notification = copy.deepcopy(notification)
        notification.update(notification['variants'][variant - 1])
        for key_to_remove in ('sample', 'variants'):
            notification.pop(key_to_remove, None)
        return notification


def _can_be_shown(notification):
    return notification.get('title', None) and notification.get('message', None)


def _generate_version(groups):
    version = time.strftime('%Y%m%d%H%M', time.gmtime())
    for group in groups:
        version += '-%s/%s' % (group['id'], group['variant'])
    return version


def _get_notifications_to_send(notifications, groups):
    active_variant = _get_active_variant(notifications, groups)
    if active_variant:
        return [active_variant] if _can_be_shown(active_variant) else []

    notifications_to_send = []
    for notification in notifications:
        if not _can_be_shown(notification):
            continue
        if 'variants' in notification:
            notification = copy.deepcopy(notification)
            del notification['variants']
        notifications_to_send.append(notification)
    return notifications_to_send


def _create_response(notifications, groups):
    return {
        'version': _generate_version(groups),
        'notifications': _get_notifications_to_send(notifications, groups),
    }


@url_handler('/notification.json')
def notification(environ, start_response):
    params = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
    version = params.get('lastVersion', [''])[0]
    notifications = load_notifications()
    groups = _determine_groups(version, notifications)
    notifications = [x for x in notifications if not x.get('inactive', False)]
    _assign_groups(groups, notifications)
    response = _create_response(notifications, groups)
    response_headers = [('Content-Type', 'application/json; charset=utf-8'),
                        ('ABP-Notification-Version', response['version'])]
    response_body = json.dumps(response, ensure_ascii=False, indent=2,
                               separators=(',', ': '),
                               sort_keys=True).encode('utf-8')
    start_response('200 OK', response_headers)
    return response_body
