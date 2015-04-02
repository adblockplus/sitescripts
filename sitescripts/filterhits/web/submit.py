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

import json
import os
import tempfile
import time
import traceback
from datetime import datetime
from errno import EEXIST

import MySQLdb

from sitescripts.web import url_handler
from sitescripts.utils import get_config, setupStderr
from sitescripts.filterhits import db, geometrical_mean
from sitescripts.filterhits.web import common

def log_filterhits(data, basepath, query_string):
  """
  This logs the provided filterhits data as JSON to a file named after
  the current timestamp in a directory named after the current date.
  """
  now = time.gmtime()

  dir_name = time.strftime("%Y-%m-%d", now)
  path = os.path.join(basepath, dir_name)
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno != EEXIST:
      raise

  with tempfile.NamedTemporaryFile(
    prefix = str(int(time.mktime(now))) + "-",
    suffix = ".log",
    dir = path,
    delete = False
  ) as f:
    print >> f, "[%s] %s" % (time.strftime("%d/%b/%Y:%H:%M:%S", now), query_string)
    json.dump(data, f)
    return f.name

@url_handler("/submit")
def submit(environ, start_response):
  setupStderr(environ["wsgi.errors"])
  config = get_config()

  # Check that this is a POST request
  if environ["REQUEST_METHOD"] != "POST":
    return common.show_error("Unsupported request method", start_response)

  # Parse the submitted JSON
  try:
    data = json.loads(environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"])))
  except (KeyError, IOError, ValueError):
    return common.show_error("Error while parsing JSON data.", start_response)

  # Make sure the submitted data was contained within an object at least
  if not isinstance(data, dict):
    return common.show_error("Error, data must be contained within an object.", start_response)

  # Log the data to a file
  log_dir = config.get("filterhitstats", "log_dir")
  try:
    log_file = log_filterhits(data, log_dir, environ.get("QUERY_STRING", ""))
  except (OSError, IOError):
    traceback.print_exc()
    return common.show_error("Failed to write data to log file!", start_response,
                             "500 Logging error")

  # Update the geometrical_mean aggregations in the database
  interval = config.get("filterhitstats", "interval")
  try:
    db_connection = db.connect()
    try:
      db.write(db_connection, geometrical_mean.update(interval, data))
    finally:
      db_connection.close()
  except:
    # Updating the aggregations in the database failed for whatever reason,
    # log the details but continue to return 204 to the client to avoid the
    # re-transmission of data.
    processing_error_log = os.path.join(config.get("filterhitstats", "log_dir"),
                                        "processing-errors.log")
    with open(processing_error_log, "a+") as f:
      message = "Problem processing data file %s:\n%s" % (
        log_file, traceback.format_exc()
      )
      print >> f, "[%s] %s" % (datetime.now().strftime("%d/%b/%Y:%H:%M:%S %z"), message)

  # Send back a 204 No Content
  start_response("204 No Content", [])
  return []
