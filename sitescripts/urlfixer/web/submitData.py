# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
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
import MySQLdb
import json
from urlparse import parse_qs
from sitescripts.web import url_handler
from sitescripts.utils import cached, get_config, setupStderr


@url_handler('/submitData')
def submit_data(environ, start_response):
    setupStderr(environ['wsgi.errors'])

    if environ['REQUEST_METHOD'].upper() != 'POST':
        return showError('Unsupported request method', start_response)

    params = parse_qs(environ.get('QUERY_STRING', ''))
    requestVersion = params.get('version', ['0'])[0]
    data = '{}'
    try:
        data_length = int(environ.get('CONTENT_LENGTH', '0'))
    except ValueError:
        data_length = 0
    if data_length != 0:
        data = environ['wsgi.input'].read(data_length)
    try:
        data = json.loads(data)
    except json.decoder.JSONDecodeError:
        return showError('Error while parsing JSON data.', start_response)

    db = _get_db()

    for domain, status in data.iteritems():
        process_domain(db, domain, status)

    db.commit()

    response_headers = [('Content-type', 'text/plain')]
    start_response('200 OK', response_headers)
    return []


def process_domain(db, domain, status):
    domain_id = _get_domain_id(db, domain)
    _increment_entry(db, domain_id, status)


def showError(message, start_response):
    start_response('400 Processing Error', [('Content-Type', 'text/plain; charset=utf-8')])
    return [message.encode('utf-8')]


def _get_db():
    database = get_config().get('urlfixer', 'database')
    dbuser = get_config().get('urlfixer', 'dbuser')
    dbpasswd = get_config().get('urlfixer', 'dbpassword')
    if os.name == 'nt':
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset='utf8', named_pipe=True)
    else:
        return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                               use_unicode=True, charset='utf8')


def _get_domain_id(db, domain):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id FROM domains WHERE domain = %s', domain)
    result = cursor.fetchone()
    if result == None:
        cursor.execute('INSERT INTO domains(domain) VALUES (%s)', domain)
        return db.insert_id()
    else:
        return result['id']


def _increment_entry(db, domain_id, status):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('INSERT INTO corrections(domain, status, curr_month, prev_month, curr_year, prev_year) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE curr_month = curr_month + 1, curr_year = curr_year + 1', (domain_id, status, 1, 0, 1, 0))
