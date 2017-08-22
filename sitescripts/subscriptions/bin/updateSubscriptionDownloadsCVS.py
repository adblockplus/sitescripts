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
import subprocess
import tempfile
import shutil
from sitescripts.utils import get_config, setupStderr

if __name__ == '__main__':
    setupStderr()

    source = get_config().get('subscriptionDownloads', 'outdir')
    cvsroot = get_config().get('subscriptionDownloads', 'cvsroot')
    cvsdir = get_config().get('subscriptionDownloads', 'cvsdir')
    dest = tempfile.mkdtemp()
    try:
        os.chdir(os.path.dirname(dest))   # Yes, CVS sucks
        subprocess.check_call(['cvs', '-Q', '-d', cvsroot, 'checkout', '-d', os.path.basename(dest), cvsdir])
        os.chdir(dest)
        result = subprocess.check_output(['rsync', '-a', '--delete', '--out-format=%o %n', '--exclude=CVS', source + os.path.sep, dest])
        for line in result.split('\n'):
            match = re.search(r'^(\S+)\s+(.*)', line)
            if match and match.group(1) == 'send':
                subprocess.check_call(['cvs', '-Q', 'add', match.group(2)])
            elif match and match.group(1) == 'del.':
                subprocess.check_call(['cvs', '-Q', 'remove', match.group(2)])
        subprocess.check_call(['cvs', '-Q', 'commit', '-m', 'Uploading subscription updates'])
    finally:
        if os.path.exists(dest):
            shutil.rmtree(dest, True)
