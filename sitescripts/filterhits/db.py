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

import MySQLdb

from sitescripts.utils import get_config

def connect():
  config = get_config()
  return MySQLdb.connect(
    user=config.get("filterhitstats", "dbuser"),
    passwd=config.get("filterhitstats", "dbpassword"),
    db=config.get("filterhitstats", "database"),
    use_unicode=True, charset="utf8"
  )

def query(db, sql, *params, **kwargs):
  """
  Executes the query given by the provided SQL and returns the results.
  If dict_result keyword argument is provided + True the results will be
  returned as a tuple of dictionaries, otherwise a tuple of tuples.
  """
  if kwargs.get("dict_result"):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
  else:
    cursor = db.cursor()
  try:
    cursor.execute(sql, params)
    db.commit()
    return cursor.fetchall()
  finally:
    cursor.close()

def write(db, queries):
  """
  This writes a given iteratable object of tuples containing SQL
  strings and any required parameters to the database. All queries will
  be run as one transaction and rolled back on error.
  """
  try:
    cursor = db.cursor()
    try:
      for query in queries:
        sql, params = query[0], query[1:]
        cursor.execute(sql, params)
      db.commit()
    finally:
      cursor.close()
  except MySQLdb.Error:
    db.rollback()
    raise
