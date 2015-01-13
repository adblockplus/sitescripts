# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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

import os, subprocess
from sitescripts.utils import get_config, setupStderr
from sitescripts.subscriptions.bin.processTemplate import writeSubscriptions
from tempfile import mkdtemp
from shutil import rmtree

def updateRecommendations():
  repository = get_config().get('extensions', 'abp_repository')
  tempdir = mkdtemp(prefix='adblockplus')
  try:
    subprocess.check_call(['hg', 'clone', '-q', '-U', repository, tempdir])
    subprocess.check_call(['hg', 'up', '-q', '-R', tempdir, '-r', 'default'])
    writeSubscriptions('recommendations', os.path.join(tempdir, 'chrome', 'content', 'ui', 'subscriptions.xml'))
    if subprocess.check_output(['hg', 'stat', '-R', tempdir]) != '':
      subprocess.check_call(['hg', 'commit', '-q', '-R', tempdir, '-u', 'hgbot', '-m', 'Updated list of recommended subscriptions'])
      subprocess.check_call(['hg', 'push', '-q', '-R', tempdir])
  finally:
    rmtree(tempdir)

if __name__ == '__main__':
  setupStderr()
  updateRecommendations()
