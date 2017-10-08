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

import MySQLdb
import os
import re
import subprocess
from sitescripts.utils import cached, get_config


@cached(600)
def _get_db():
    database = get_config().get('crawler', 'database')
    dbuser = get_config().get('crawler', 'dbuser')
    dbpasswd = get_config().get('crawler', 'dbpassword')
    if os.name == 'nt':
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset='utf8', named_pipe=True)
    else:
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset='utf8')


def _get_cursor():
    return _get_db().cursor(MySQLdb.cursors.DictCursor)


def _hg(args):
    return subprocess.check_output(['hg'] + args)


def _extract_sites(easylist_dir):
    os.chdir(easylist_dir)
    process = _hg(['log', '--template', '{desc}\n'])
    urls = set([])

    for line in process.stdout:
        match = re.search(r'\b(https?://\S*)', line)
        if not match:
            continue

        url = match.group(1).strip()
        urls.add(url)

    return urls


def _insert_sites(site_urls):
    cursor = _get_cursor()
    for url in site_urls:
        cursor.execute('INSERT IGNORE INTO crawler_sites (url) VALUES (%s)', url)
    _get_db().commit()


if __name__ == '__main__':
    easylist_dir = get_config().get('crawler', 'easylist_repository')
    site_urls = _extract_sites(easylist_dir)
    _insert_sites(site_urls)
