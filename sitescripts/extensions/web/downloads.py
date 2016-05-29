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

import re
import time
import posixpath
import urlparse
import threading
import traceback
from ConfigParser import SafeConfigParser
from sitescripts.web import url_handler
from sitescripts.extensions.utils import getDownloadLinks

links = {}
UPDATE_INTERVAL = 10 * 60   # 10 minutes


@url_handler('/latest/')
def handle_request(environ, start_response):
    request = urlparse.urlparse(environ.get('REQUEST_URI', ''))
    basename = posixpath.splitext(posixpath.basename(request.path))[0]
    if basename in links:
        start_response('302 Found', [('Location', links[basename].encode('utf-8'))])
    else:
        start_response('404 Not Found', [])
    return []


def _get_links():
    parser = SafeConfigParser()
    getDownloadLinks(parser)
    result = {}
    for section in parser.sections():
        result[section] = parser.get(section, 'downloadURL')
    return result


def _update_links():
    global links

    while True:
        try:
            links = _get_links()
        except:
            traceback.print_exc()
        time.sleep(UPDATE_INTERVAL)

t = threading.Thread(target=_update_links)
t.daemon = True
t.start()
