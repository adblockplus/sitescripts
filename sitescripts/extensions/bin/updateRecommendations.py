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
import subprocess
from sitescripts.utils import get_config
from sitescripts.subscriptions.bin.processTemplate import writeSubscriptions
from tempfile import mkdtemp
from shutil import rmtree


def update_recommendations():
    repository = get_config().get('extensions', 'subscriptions_repository')
    path = get_config().get('extensions', 'subscriptions_path').split('/')
    tempdir = mkdtemp(prefix='adblockplus')
    try:
        subprocess.check_call([
            'hg', 'clone', '-q', '-U', repository, tempdir,
        ])
        subprocess.check_call([
            'hg', 'up', '-q', '-R', tempdir, '-r', 'master',
        ])
        writeSubscriptions('recommendations', os.path.join(tempdir, *path))
        if subprocess.check_output(['hg', 'stat', '-R', tempdir]) != '':
            subprocess.check_call([
                'hg', 'commit', '-q', '-R', tempdir, '-u', 'hgbot',
                '-m', 'Noissue - Updated list of recommended subscriptions',
            ])
            subprocess.check_call([
                'hg', 'push', '-q', '-R', tempdir, '-r', 'master',
            ])
    finally:
        rmtree(tempdir)


if __name__ == '__main__':
    update_recommendations()
