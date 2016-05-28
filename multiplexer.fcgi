#!/usr/bin/env python

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

import os
import re
from flup.server.fcgi import WSGIServer

from sitescripts.web import multiplex

bindAddress = os.environ.get('FCGI_BIND_ADDRESS')
if bindAddress:
    match = re.search(r'^(.*?):(\d+)$', bindAddress)
    if match:
        bindAddress = (match.group(1), int(match.group(2)))

srv = WSGIServer(multiplex, debug=False, bindAddress=bindAddress)

if __name__ == '__main__':
    srv.run()
