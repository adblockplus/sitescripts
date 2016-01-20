# coding: utf-8

# This file is part of the Adblock Plus web scripts,
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

import json
import os
import traceback
from urlparse import parse_qsl

import MySQLdb

from sitescripts.web import url_handler
from sitescripts.utils import cached, setupStderr
from sitescripts.filterhits import db
from sitescripts.filterhits.web import common

def query(domain=None, filter=None, skip=0, take=20, order="DESC", order_by="frequency", **_):
  """
  Returns the SQL and parameters needed to perform a query of the filterhits data.
  """
  sql = """SELECT SQL_CALC_FOUND_ROWS domain, filter, frequency
           FROM frequencies as freq
           LEFT JOIN filters as f ON f.sha1=freq.filter_sha1
           %s
           ORDER BY %s
           LIMIT %%s, %%s"""

  where = zip(*[("%s LIKE %%s" % s, "%%%s%%" % p) for s, p in (("domain", domain),
                                                               ("filter", filter)) if p])
  if where:
    where_fields, params = where
    where_sql = "WHERE " + " AND ".join(where_fields)
  else:
    where_sql = ""
    params = []

  order = order.upper() if order.upper() in ("ASC", "DESC") else "ASC"
  if order_by not in ["filter", "domain", "frequency"]:
    order_by = "frequency"
  order_by_sql = "`%s` %s" % (order_by, order)

  params = list(params) + [int(skip), int(take)]
  return [sql % (where_sql, order_by_sql)] + params

@url_handler("/query")
def query_handler(environ, start_response):
  setupStderr(environ["wsgi.errors"])
  params = dict(parse_qsl(environ.get("QUERY_STRING", "")))

  try:
    db_connection = db.connect()
    try:
      results = db.query(db_connection, *query(**params), dict_result=True)
      total = db.query(db_connection, "SELECT FOUND_ROWS()")[0][0]
    finally:
      db_connection.close()
  except MySQLdb.Error:
    traceback.print_exc()
    return common.show_error("Failed to query database!", start_response,
                             "500 Database error")

  try:
    echo = int(params["echo"])
  except (ValueError, KeyError):
    echo = 0

  response_headers = [("Content-type", "application/json; charset=utf-8")]
  start_response("200 OK", response_headers)
  return [json.dumps({"results": results, "echo": echo,
                      "total": total, "count": len(results)},
                     ensure_ascii=False).encode("utf-8")]
