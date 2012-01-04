# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

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
