# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2014 Eyeo GmbH
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

import os, re, subprocess, tempfile, shutil, zipfile
from StringIO import StringIO
from ...utils import get_config, setupStderr
from ..combineSubscriptions import combine_subscriptions

class MercurialSource:
  _prefix = "./"

  def __init__(self, repo):
    command = ["hg", "-R", repo, "archive", "-r", "default",
        "-t", "uzip", "-p", ".", "-"]
    data = subprocess.check_output(command)
    self._archive = zipfile.ZipFile(StringIO(data), mode="r")

  def close(self):
    self._archive.close()

  def read_file(self, filename):
    return self._archive.read(self._prefix + filename).decode("utf-8")

  def list_top_level_files(self):
    for filename in self._archive.namelist():
      filename = filename[len(self._prefix):]
      if "/" not in filename:
        yield filename

if __name__ == "__main__":
  setupStderr()

  source_repos = {}
  for option, value in get_config().items("subscriptionDownloads"):
    if option.endswith("_repository"):
      source_repos[re.sub(r"_repository$", "", option)] = MercurialSource(value)

  basedir = get_config().get("subscriptionDownloads", "outdir")
  destination = os.path.join(basedir, "data")
  try:
    combine_subscriptions(source_repos, destination, tempdir=basedir)
  finally:
    for source in source_repos.itervalues():
      source.close()
