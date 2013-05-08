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

import os, re, subprocess, urllib
from sitescripts.utils import get_config, setupStderr
from ConfigParser import SafeConfigParser, NoOptionError
from StringIO import StringIO

def readStatsFile(path):
  result = SafeConfigParser()
  match = re.search(r'^ssh://(\w+)@([^/:]+)(?::(\d+))?', path)
  if match:
    command = ['ssh', '-q', '-o' 'NumberOfPasswordPrompts 0', '-T', '-k', '-l', match.group(1), match.group(2)]
    if match.group(3):
      command[1:1] = ['-P', match.group(3)]
    (data, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    result.readfp(StringIO(data))
  elif path.startswith('http://') or path.startswith('https://'):
    result.readfp(urllib.urlopen(path))
  elif os.path.exists(path):
    result.read(path)
  return result

def getStatsFiles():
  config = get_config()

  for option in config.options('subscriptionStats'):
    match = re.search(r'^mirror_(.*)', option, re.I)
    if match:
      yield (match.group(1), config.get('subscriptionStats', option))

def mergeStatsFile(mirrorName, config1, config2):
  def increaseOption(section, option, increase):
    if config1.has_option(section, option):
      oldval = config1.getint(section, option)
      config1.set(section, option, str(oldval + increase))
    else:
      config1.set(section, option, str(increase))

  for section in config2.sections():
    if not config1.has_section(section):
      config1.add_section(section)
    for option in config2.options(section):
      increase = config2.getint(section, option)
      increaseOption(section, option, increase)

      match = re.search(r'^(\S+) (hits|bandwidth)$', option, re.I)
      if match:
        increaseOption(section, '%s %s mirror %s' % (match.group(1), match.group(2), mirrorName), increase)

if __name__ == '__main__':
  setupStderr()

  result = readStatsFile(get_config().get('subscriptionStats', 'mainFile'))
  for (mirrorName, statsFile) in getStatsFiles():
    mergeStatsFile(mirrorName, result, readStatsFile(statsFile))
  file = open(get_config().get('subscriptionStats', 'mainFile'), 'wb')
  result.write(file)
