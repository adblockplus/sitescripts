# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2013 Eyeo GmbH
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

import os, re, subprocess, tempfile, shutil
from sitescripts.utils import get_config, setupStderr

if __name__ == '__main__':
  setupStderr()

  source = get_config().get('subscriptionDownloads', 'outdir')
  cvsroot = get_config().get('subscriptionDownloads', 'cvsroot')
  cvsdir = get_config().get('subscriptionDownloads', 'cvsdir')
  dest = tempfile.mkdtemp()
  try:
    os.chdir(os.path.dirname(dest))   # Yes, CVS sucks
    subprocess.Popen(['cvs', '-Q', '-d', cvsroot, 'checkout', '-d', os.path.basename(dest), cvsdir]).communicate()
    os.chdir(dest)
    (result, dummy) = subprocess.Popen(['rsync', '-a', '--delete', '--out-format=%o %n', '--exclude=CVS', source + '/', dest], stdout=subprocess.PIPE).communicate()
    for line in result.split('\n'):
      match = re.search(r'^(\S+)\s+(.*)', line)
      if match and match.group(1) == 'send':
        subprocess.Popen(['cvs', '-Q', 'add', match.group(2)]).communicate()
      elif match and match.group(1) == 'del.':
        subprocess.Popen(['cvs', '-Q', 'remove', match.group(2)]).communicate()
    subprocess.Popen(['cvs', '-Q', 'commit', '-m', 'Uploading subscription updates'], stdout=subprocess.PIPE).communicate()
  finally:
    if os.path.exists(dest):
      shutil.rmtree(dest, True)
