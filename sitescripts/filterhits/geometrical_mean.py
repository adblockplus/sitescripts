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

from sitescripts.filterhits import db

def update(interval, data):
  """
  Generator that provides all the SQL and parameters needed to update the
  aggregations for the given data + interval in the database.
  """
  for filter, filter_data in data['filters'].iteritems():
    yield ("""INSERT IGNORE INTO `filters`
              (filter, sha1) VALUES (%s, UNHEX(SHA1(filter)))""", filter)

    domains = itertools.chain(filter_data.get("thirdParty", {}).iteritems(),
                              filter_data.get("firstParty", {}).iteritems())
    for domain, domain_data in domains:
      yield ("""INSERT INTO `frequencies`
                (filter_sha1, domain, frequency, timestamp)
                VALUES (UNHEX(SHA1(%s)), %s, %s, FROM_UNIXTIME(%s))
                ON DUPLICATE KEY UPDATE
                frequency = (
                  POW(frequency, 1 - (UNIX_TIMESTAMP(VALUES(timestamp)) -
                                      UNIX_TIMESTAMP(timestamp)) / %s) *
                  POW(VALUES(frequency), (UNIX_TIMESTAMP(VALUES(timestamp)) -
                                          UNIX_TIMESTAMP(timestamp)) / %s)),
                timestamp = VALUES(timestamp)""",
             filter, domain, domain_data["hits"],
             int(domain_data["latest"] / 1000), interval, interval)
