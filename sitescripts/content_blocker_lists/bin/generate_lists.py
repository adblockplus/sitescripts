#!/usr/bin/env python

# This file is part of Adblock Plus <https://adblockplus.org/>,
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

from collections import OrderedDict
from contextlib import closing
import json
import os
import subprocess
import threading
import time
import re
import urllib2

from sitescripts.utils import get_config

config = dict(get_config().items('content_blocker_lists'))


def update_abp2blocklist():
    with open(os.devnull, 'w') as devnull:
        abp2blocklist_path = config['abp2blocklist_path']
        if os.path.isdir(abp2blocklist_path):
            subprocess.check_call(('hg', 'pull', '-u', '-R', abp2blocklist_path),
                                  stdout=devnull)
        else:
            subprocess.check_call(('hg', 'clone', config['abp2blocklist_url'],
                                   abp2blocklist_path), stdout=devnull)
        subprocess.check_call(('npm', 'install'), cwd=abp2blocklist_path,
                              stdout=devnull)


def download_filter_list(url):
    with closing(urllib2.urlopen(url)) as response:
        body = response.read()
    version = re.search(r'^(?:[^[!])|^!\s*Version:\s*(.+)$',
                        body, re.MULTILINE).group(1)
    return body, url, version


def generate_metadata(filter_lists, expires):
    metadata = OrderedDict((
        ('version', time.strftime('%Y%m%d%H%M', time.gmtime())),
        ('expires', expires),
        ('sources', []),
    ))
    for body, url, version in filter_lists:
        metadata['sources'].append({'url': url, 'version': version})
    return metadata


def pipe_in(process, filter_lists):
    try:
        for body, _, _ in filter_lists:
            print >>process.stdin, body
    finally:
        process.stdin.close()


def write_block_list(filter_lists, path, expires):
    block_list = generate_metadata(filter_lists, expires)
    process = subprocess.Popen(('node', 'abp2blocklist.js'),
                               cwd=config['abp2blocklist_path'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    threading.Thread(target=pipe_in, args=(process, filter_lists)).start()
    block_list['rules'] = json.load(process.stdout)
    if process.wait():
        raise Exception('abp2blocklist returned %s' % process.returncode)

    with open(path, 'wb') as destination_file:
        json.dump(block_list, destination_file, indent=2, separators=(',', ': '))


if __name__ == '__main__':
    update_abp2blocklist()

    easylist = download_filter_list(config['easylist_url'])
    exceptionrules = download_filter_list(config['exceptionrules_url'])

    write_block_list([easylist],
                     config['easylist_content_blocker_path'],
                     config['easylist_content_blocker_expires'])
    write_block_list([easylist, exceptionrules],
                     config['combined_content_blocker_path'],
                     config['combined_content_blocker_expires'])
