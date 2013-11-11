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
  destination = tempfile.mkdtemp(prefix="data.", dir=basedir)
  if hasattr(os, "chmod"):
    os.chmod(destination, 0755)
  try:
    combine_subscriptions(source_repos, destination)
  except:
    shutil.rmtree(destination, ignore_errors=True)
    raise
  finally:
    for source in source_repos.itervalues():
      source.close()

  symbolic_link = os.path.join(basedir, "data")
  symbolic_link_new = os.path.join(basedir, "data_new")
  symbolic_link_old = os.path.join(basedir, "data_old")
  if os.path.islink(symbolic_link):
    orig_data = os.path.join(basedir, os.readlink(symbolic_link))
  else:
    orig_data = None

  os.symlink(os.path.relpath(destination, basedir), symbolic_link_new)
  os.rename(symbolic_link_new, symbolic_link)

  # We need to keep the original data around until next update, otherwise rsync
  # will complain if it is already syncing that directory.
  if orig_data:
    if os.path.islink(symbolic_link_old):
      remove_dir = os.path.join(basedir, os.readlink(symbolic_link_old))
      os.remove(symbolic_link_old)
    else:
      remove_dir = None

    os.symlink(os.path.relpath(orig_data, basedir), symbolic_link_old)
    if remove_dir:
      shutil.rmtree(remove_dir)
