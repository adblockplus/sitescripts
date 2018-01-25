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

import codecs
import datetime
import os
import re
import subprocess
import tarfile
import traceback
from StringIO import StringIO

from sitescripts.utils import get_config


def _parse_targetspec(value, name):
    target = {}

    items = [
        (r'^(extension|application|platform)(=)(.+)$', {
            '=': lambda k, v: {k: v},
        }),
        (r'^(extension|application|platform)Version(=|\>=|\<=)(.+)$', {
            '>=': lambda k, v: {k + 'MinVersion': v},
            '<=': lambda k, v: {k + 'MaxVersion': v},
            '=': lambda k, v: {k + 'MinVersion': v, k + 'MaxVersion': v},
        }),
        (r'^(blockedTotal)(=|\>=|\<=)(\d+)$', {
            '>=': lambda k, v: {k + 'Min': int(v)},
            '<=': lambda k, v: {k + 'Max': int(v)},
            '=': lambda k, v: {k + 'Min': int(v), k + 'Max': int(v)},
        }),
        (r'^(locales)(=)([\w\-,]+)$', {
            '=': lambda k, v: {k: v.split(',')},
        }),
    ]

    try:
        for spec in value.split():
            for regx, ops in items:
                m = re.search(regx, spec)
                if m:
                    key, op, value = m.groups()
                    target.update(ops[op](key, value))
                    break
            else:
                raise ValueError
    except (KeyError, ValueError):
        raise Exception(
            "Unknown target specifier '{}' in file '{}'".format(spec, name))

    return target


def _parse_notification(data, name):
    notification = {'id': name, 'severity': 'information', 'message': {}, 'title': {}}
    current = notification

    for line in data:
        if not re.search(r'\S', line):
            continue

        if re.search(r'^\[.*\]$', line):
            current = {'title': {}, 'message': {}}
            notification.setdefault('variants', []).append(current)
            continue

        if line.find('=') < 0:
            raise Exception("Could not process line '%s' in file '%s'" % (line.strip(), name))

        key, value = map(unicode.strip, line.split('=', 1))
        is_variant = current != notification

        if key == 'inactive' and not is_variant:
            current['inactive'] = value.lower() not in ('', '0', 'no', 'false', 'off')
        elif key == 'severity':
            if value not in ('information', 'critical', 'normal', 'relentless'):
                raise Exception("Unknown severity value '%s' in file '%s'" % (value, name))
            current['severity'] = value
        elif key == 'links':
            current['links'] = value.split()
        elif key.startswith('title.'):
            locale = key[len('title.'):]
            current['title'][locale] = value
        elif key.startswith('message.'):
            locale = key[len('message.'):]
            current['message'][locale] = value
        elif key == 'target':
            target = _parse_targetspec(value, name)
            if 'targets' in notification:
                current['targets'].append(target)
            else:
                current['targets'] = [target]
        elif key == 'sample' and is_variant:
            current['sample'] = float(value)
        elif key in ['start', 'end']:
            current[key] = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')
        elif key == 'interval':
            current[key] = int(value)
        elif key == 'urls':
            current['urlFilters'] = [
                v.upper() + '^$document'
                for v in value.split()
            ]
        else:
            raise Exception("Unknown parameter '%s' in file '%s'" % (key, name))

    for text_key in ('title', 'message'):
        def has_default_locale(variant):
            return 'en-US' in variant[text_key]
        if not has_default_locale(notification):
            variants = notification.get('variants', [])
            if not all(map(has_default_locale, variants)):
                raise Exception('No %s for en-US (default language) '
                                "in file '%s'" % (text_key, name))
    return notification


def load_notifications():
    repo = get_config().get('notifications', 'repository')
    command = ['hg', '-R', repo, 'archive', '-r', 'default', '-t', 'tar',
               '-p', '.', '-X', os.path.join(repo, '.hg_archival.txt'), '-']
    data = subprocess.check_output(command)

    notifications = []
    with tarfile.open(mode='r:', fileobj=StringIO(data)) as archive:
        for fileinfo in archive:
            name = fileinfo.name
            if name.startswith('./'):
                name = name[2:]

            if fileinfo.type == tarfile.REGTYPE:
                data = codecs.getreader('utf8')(archive.extractfile(fileinfo))
                try:
                    notification = _parse_notification(data, name)
                    if not 'inactive' in notification:
                        current_time = datetime.datetime.now()
                        start = notification.pop('start', current_time)
                        end = notification.pop('end', current_time)
                        if not start <= current_time <= end:
                            notification['inactive'] = True
                    notifications.append(notification)
                except:
                    traceback.print_exc()
    return notifications
