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

import itertools
import json
import logging
import os
import sys

import MySQLdb

from sitescripts.utils import get_config
from sitescripts.filterhits import db, geometrical_mean

_last_log_file = None

def log_files(dir):
  """
  Provides a generator of filter hits log files for the given directory.
  Works recursively, relative path of log file is returned.
  """
  for root, subdirs, files in os.walk(dir):
    for f in files:
      if os.path.splitext(f)[1] == ".log" and f[0].isdigit():
        yield os.path.join(root, f)

def read_data(log_file):
  """
  Read, parse and return the JSON data for the given log file name.
  (As a side effect sets the global _last_log_file to the log file name.)
  """
  global _last_log_file
  try:
    with open(log_file, "r") as f:
      f.readline()
      data = json.load(f)
      # Keep track of the current log file in global variable in case we need to
      # identify it later if there's a problem. (This works because the files are
      # processed lazily.)
      _last_log_file = log_file
  except IOError:
    sys.exit("Could not read log file %s" % log_file)
  return data

if __name__ == "__main__":
  if not len(sys.argv) == 2:
    print "Usage: python -m sitescripts.filterhits.bin.reprocess_logs /path/to/logs"
    sys.exit(1)

  interval = get_config().get("filterhitstats", "interval")

  def read_update(f):
    return geometrical_mean.update(interval, read_data(f))

  if sys.argv[1].endswith(".log"):
    sql = read_update(sys.argv[1])
  else:
    sql = itertools.chain.from_iterable(itertools.imap(read_update,
                                                       log_files(sys.argv[1])))

  db_connection = db.connect()

  try:
    db.write(db_connection, sql)
  except:
    logging.error("Failed to process file %s, all changes rolled back." % _last_log_file)
    raise
  finally:
    db_connection.close()
