# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import os, subprocess, tempfile, shutil
from sitescripts.utils import get_config, setupStderr
from sitescripts.subscriptions.combineSubscriptions import combineSubscriptions

if __name__ == '__main__':
  setupStderr()

  sourceRepo = get_config().get('easylist', 'repository')
  destRepo = get_config().get('easylist', 'outdir')

  sourceTemp = tempfile.mkdtemp()
  destTemp = tempfile.mkdtemp()
  try:
    subprocess.Popen(['hg', 'archive', '-q', '-R', sourceRepo, '-r', 'default', sourceTemp]).communicate()
    subprocess.Popen(['rsync', '-a', destRepo + '/', destTemp]).communicate()
    combineSubscriptions(sourceTemp, destTemp)
    subprocess.Popen(['rsync', '-au', destTemp + '/', destRepo]).communicate()
  finally:
    if os.path.exists(sourceTemp):
      shutil.rmtree(sourceTemp, True)
    if os.path.exists(destTemp):
      shutil.rmtree(destTemp, True)
