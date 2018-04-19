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
import json
import time

from sitescripts.notifications.parser import load_notifications
from sitescripts.utils import get_config, setupStderr


def generate_notifications(path):
    notifications = load_notifications()
    # Ignoring notifications with variants here - we can only process those in a
    # URL handler.
    notifications = [x for x in notifications if 'variants' in x]
    output = {
        'notifications': notifications,
        'version': time.strftime('%Y%m%d%H%M', time.gmtime()),
    }
    with codecs.open(path, 'wb', encoding='utf-8') as file:
        json.dump(output, file, ensure_ascii=False, indent=2,
                  separators=(',', ': '), sort_keys=True)


if __name__ == '__main__':
    setupStderr()
    output = get_config().get('notifications', 'output')
    generate_notifications(output)
