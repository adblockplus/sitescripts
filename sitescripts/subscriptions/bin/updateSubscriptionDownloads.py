# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

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
      subprocess.Popen(['hg', 'archive', '-R', repoDir, '-r', 'default', tempDir]).communicate()
    subprocess.Popen(['rsync', '-a', '--delete', destDir + '/', destTemp]).communicate()
    combineSubscriptions(sourceTemp, destTemp)
    subprocess.Popen(['rsync', '-au', '--delete', destTemp + '/', destDir]).communicate()
  finally:
    for tempDir in sourceTemp.itervalues():
      if os.path.exists(tempDir):
        shutil.rmtree(tempDir, True)
    if destTemp and os.path.exists(destTemp):
      shutil.rmtree(destTemp, True)
