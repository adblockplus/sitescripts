# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

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

  yield (config.get('subscriptionStats', 'mirrorName'), config.get('subscriptionStats', 'tempFile'))

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
