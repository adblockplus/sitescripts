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

import os
import re
import sys
import subprocess
import tarfile
from StringIO import StringIO
from sitescripts.utils import get_config, setupStderr


def generate_data(repo):
    command = ['hg', '-R', repo, 'archive', '-r', 'default', '-t', 'tar', '-p', '.', '-']
    data = subprocess.check_output(command)

    users = {}
    repos = []
    with tarfile.open(mode='r:', fileobj=StringIO(data)) as archive:
        for fileinfo in archive:
            name = fileinfo.name
            if name.startswith('./'):
                name = name[2:]

            if fileinfo.type == tarfile.REGTYPE and name.startswith('users/'):
                name = os.path.basename(name).lower()
                options = []
                match = re.search(r'^(.*)\[(.*)\]$', name)
                if match:
                    name = match.group(1)
                    options = match.group(2).split(',')

                user = {
                    'name': name,
                    'keytype': 'rsa',
                    'disabled': False,
                    'trusted': False,
                    'repos': [],
                }
                for option in options:
                    if option == 'dsa':
                        user['keytype'] = 'dsa'
                    elif option == 'disabled':
                        user['disabled'] = True
                    elif option == 'trusted':
                        user['trusted'] = True
                    else:
                        print >>sys.stderr, 'Unknown user option: %s' % option
                user['key'] = re.sub(r'\s', '', archive.extractfile(fileinfo).read())
                users[name] = user
            elif fileinfo.type == tarfile.REGTYPE and name.startswith('repos/'):
                repos.append(fileinfo)
            elif fileinfo.type == tarfile.REGTYPE and not name.startswith('.'):
                print >>sys.stderr, 'Unrecognized file in the repository: %s' % name

        for fileinfo in repos:
            name = os.path.basename(fileinfo.name).lower()
            repousers = archive.extractfile(fileinfo).readlines()
            for user in repousers:
                user = user.strip()
                if user == '' or user.startswith('#'):
                    continue
                if user in users:
                    users[user]['repos'].append(name)
                else:
                    print >>sys.stderr, 'Unknown user listed for repository %s: %s' % (name, user)

    for user in users.itervalues():
        if user['disabled']:
            continue
        yield 'no-pty,environment="HGUSER=%s",environment="HGREPOS=%s" %s %s\n' % (
            user['name'] if not user['trusted'] else '',
            ' '.join(user['repos']),
            'ssh-rsa' if user['keytype'] == 'rsa' else 'ssh-dss',
            user['key'],
        )


def hook(ui=None, repo=None, **kwargs):
    setupStderr()

    root = repo.root if repo != None else get_config().get('hg', 'auth_repository')
    result = generate_data(root)

    with open(get_config().get('hg', 'auth_file'), 'wb') as file:
        for s in result:
            file.write(s)


if __name__ == '__main__':
    hook()
