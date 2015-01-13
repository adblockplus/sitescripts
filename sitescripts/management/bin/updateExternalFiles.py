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

import os, subprocess, codecs, urllib
from sitescripts.utils import get_config, setupStderr
from tempfile import mkdtemp
from shutil import rmtree

def updateExternalFiles():
  settings = readSettings()
  for setting in settings.itervalues():
    tempdir = mkdtemp(prefix='external')
    try:
      repoPath = setting['targetrepository']
      targetPath = os.path.dirname(setting['targetfile'])
      filename = os.path.basename(setting['targetfile'])

      subprocess.check_call(['hg', 'clone', '-q', '-U', repoPath, tempdir])
      subprocess.check_call(['hg', 'up', '-q', '-R', tempdir, '-r', 'default'])

      path = os.path.join(tempdir, targetPath)
      if not os.path.exists(path):
        os.makedirs(path)

      path = os.path.join(path, filename)
      exists = os.path.exists(path)
      file = codecs.open(path, 'wb', encoding='utf-8')
      data = urllib.urlopen(setting['source']).read().decode('utf-8')
      file.write(data)
      file.close()

      if subprocess.check_output(['hg', 'stat', '-R', tempdir]) != '':
        message = 'Updated copy of external file %s'
        if not exists:
          message = 'Added copy of external file %s'
        subprocess.check_call(['hg', 'commit', '-q', '-A', '-R', tempdir, '-u', 'hgbot', '-m', message % filename])
        subprocess.call(['hg', 'push', '-q', '-R', tempdir])
    finally:
      rmtree(tempdir)

def readSettings():
  result = {}
  for option, value in get_config().items('externalFiles'):
    if option.find('_') < 0:
      continue
    name, setting = option.rsplit('_', 2)
    if not setting in ('source', 'targetrepository', 'targetfile'):
      continue

    if not name in result:
      result[name] = {
        'source': None,
        'targetrepository': None,
        'targetfile': None
      }
    result[name][setting] = value
  return result

if __name__ == '__main__':
  setupStderr()
  updateExternalFiles()
