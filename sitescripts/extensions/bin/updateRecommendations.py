# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import os, subprocess
from sitescripts.utils import get_config, setupStderr
from sitescripts.subscriptions.bin.processTemplate import writeSubscriptions
from tempfile import mkdtemp
from shutil import rmtree

def updateRecommendations():
  repository = get_config().get('extensions', 'abp_repository')
  tempdir = mkdtemp(prefix='adblockplus')
  try:
    subprocess.Popen(['hg', 'clone',  '-U', repository, tempdir], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'up', '-R', tempdir, '-r', 'default'], stdout=subprocess.PIPE).communicate()
    writeSubscriptions('recommendations', os.path.join(tempdir, 'chrome', 'content', 'ui', 'subscriptions.xml'))
    subprocess.Popen(['hg', 'commit', '-R', tempdir, '-u', 'hgbot', '-m', 'Updated list of recommended subscriptions'], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'push', '-R', tempdir], stdout=subprocess.PIPE).communicate()
  finally:
    rmtree(tempdir)

  repository = get_config().get('extensions', 'abpchrome_repository')
  tempdir = mkdtemp(prefix='adblockpluschrome')
  try:
    subprocess.Popen(['hg', 'clone',  '-U', repository, tempdir], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'up', '-R', tempdir, '-r', 'default'], stdout=subprocess.PIPE).communicate()
    writeSubscriptions('recommendations', os.path.join(tempdir, 'subscriptions.xml'))
    subprocess.Popen(['hg', 'commit', '-R', tempdir, '-u', 'hgbot', '-m', 'Updated list of recommended subscriptions'], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'push', '-R', tempdir], stdout=subprocess.PIPE).communicate()
  finally:
    rmtree(tempdir)

if __name__ == '__main__':
  setupStderr()
  updateRecommendations()
