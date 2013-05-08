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

import os, subprocess
from sitescripts.utils import get_config

def _get_services():
  config = get_config()
  section_name = "keep_alive_services"
  section_keys = config.options(section_name)
  default_keys = config.defaults().keys()
  keys = set(section_keys) - set(default_keys)

  services = {}
  for key in keys:
    services[key] = config.get(section_name, key)
  return services

def _process_running(pid):
  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False

if __name__ == "__main__":
  services = _get_services()
  for service in services.keys():
    pid_path = os.path.join("/var/run", services[service])
    if os.path.exists(pid_path):
      with open(pid_path) as file:
        pid_string = file.read()

      try:
        pid = int(pid_string.rstrip())
        if _process_running(pid):
          continue
      except exceptions.ValueError:
        print "'%s' is not a PID." % pid_string

    init_path = os.path.join("/etc/init.d", service)
    if not os.path.exists(init_path):
      print "%s does not exist, service is not running and cannot be started." % init_path
      continue

    print "%s is not running, starting ..." % service
    subprocess.call([init_path, "start"])
