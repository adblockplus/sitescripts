#!/usr/bin/env python

# This file is part of Adblock Plus <https://adblockplus.org/>,
# Copyright (C) 2006-2016 Eyeo GmbH
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

import os
import shutil
import subprocess

from sitescripts.utils import get_config

def read_projects(config):
  projects = {}
  for key, value in config.items("docs"):
    key_parts = key.split("_", 1)
    if len(key_parts) < 2:
      continue
    project_name, field_name = key_parts
    if field_name not in {"repository", "target_directory", "command"}:
      continue
    projects.setdefault(project_name, {})[field_name] = value
  return projects

def sync_sources(sources_dir, repository_url):
  if os.path.exists(sources_dir):
    subprocess.check_call(["hg", "pull", "--quiet",
                           "--rev", "master",
                           "--repository", sources_dir])
    subprocess.check_call(["hg", "update", "--quiet",
                           "--rev", "master",
                           "--repository", sources_dir])
  else:
    subprocess.check_call(["hg", "clone", "--quiet",
                           "--updaterev", "master",
                           repository_url, sources_dir])

def replace_dir(source_dir, target_dir):
  if not os.path.exists(target_dir):
    parent_dir = os.path.dirname(target_dir)
    try:
      os.makedirs(parent_dir)
    except OSError:
      pass
    os.rename(source_dir, target_dir)
  else:
    old_target_dir = target_dir.rstrip(os.path.sep) + ".old"
    shutil.rmtree(old_target_dir, ignore_errors=True)
    os.rename(target_dir, old_target_dir)
    os.rename(source_dir, target_dir)
    shutil.rmtree(old_target_dir)

def run_generation_command(command, sources_dir, output_dir):
  shutil.rmtree(output_dir, ignore_errors=True)
  command = command.format(output_dir=output_dir)
  subprocess.check_call(command, shell=True, cwd=sources_dir)

def generate_docs(projects, config):
  temp_directory = config.get("docs", "temp_directory")
  try:
    os.makedirs(temp_directory)
  except OSError:
    pass

  for name, data in projects.iteritems():
    sources_dir = os.path.join(temp_directory, name)
    sync_sources(sources_dir, data["repository"])
    output_dir = sources_dir.rstrip(os.path.sep) + ".docs"
    run_generation_command(data["command"], sources_dir, output_dir)
    replace_dir(output_dir, data["target_directory"])

if __name__ == "__main__":
  config = get_config()
  projects = read_projects(config)
  generate_docs(projects, config)
