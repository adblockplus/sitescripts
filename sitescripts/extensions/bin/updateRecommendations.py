# coding: utf-8

import os, subprocess
from sitescripts.utils import get_config, setupStderr
from sitescripts.subscriptions.bin.processTemplate import writeSubscriptions
from tempfile import mkdtemp
from shutil import rmtree

def updateRecommendations(repository):
  tempdir = mkdtemp(prefix='adblockplus')
  try:
    subprocess.Popen(['hg', 'clone',  '-U', repository, tempdir], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'up', '-R', tempdir, '-r', 'experimental'], stdout=subprocess.PIPE).communicate()
    writeSubscriptions('recommendations', os.path.join(tempdir, 'chrome', 'content', 'ui', 'subscriptions.xml'))
    subprocess.Popen(['hg', 'commit', '-R', tempdir, '-u', 'hgbot', '-m', 'Updated list of recommended subscriptions'], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(['hg', 'push', '-R', tempdir], stdout=subprocess.PIPE).communicate()
  finally:
    rmtree(tempdir)

if __name__ == '__main__':
  setupStderr()
  updateRecommendations(get_config().get('extensions', 'abp_repository'))
