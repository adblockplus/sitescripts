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
from sitescripts.subscriptions.combineSubscriptions import combineSubscriptions

if __name__ == '__main__':
  setupStderr()

  sourceRepos = {}
  for option, value in get_config().items('subscriptionDownloads'):
    if option.endswith('_repository'):
      sourceRepos[re.sub(r'_repository$', '', option)] = value
  destDir = get_config().get('subscriptionDownloads', 'outdir')

  sourceTemp = {}
  destTemp = None
  try:
    destTemp = tempfile.mkdtemp()
    for repoName, repoDir in sourceRepos.iteritems():
      tempDir = tempfile.mkdtemp()
      sourceTemp[repoName] = tempDir
      subprocess.check_call(['hg', 'archive', '-R', repoDir, '-r', 'default', tempDir])
    subprocess.check_call(['rsync', '-a', '--delete', destDir + os.path.sep, destTemp])
    combineSubscriptions(sourceTemp, destTemp)
    subprocess.check_call(['rsync', '-au', '--delete', destTemp + os.path.sep, destDir])
  finally:
    for tempDir in sourceTemp.itervalues():
      if os.path.exists(tempDir):
        shutil.rmtree(tempDir, True)
    if destTemp and os.path.exists(destTemp):
      shutil.rmtree(destTemp, True)
