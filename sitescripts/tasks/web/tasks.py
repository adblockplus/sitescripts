# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb, json, re, os
from sitescripts.utils import get_config, cached, setupStderr, get_template
from sitescripts.web import url_handler
from urlparse import parse_qs
from datetime import date, timedelta

@url_handler('/tasks/')
def showTaskListing(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  if environ['REQUEST_METHOD'].upper() == 'POST':
    if not environ.get('HTTP_X_SAME_ORIGIN'):
      return error(start_response, 'Only same-origin requests are allowed')
    params = parse_qs(environ.get('QUERY_STRING', ''))
    action = params.get('action', [''])[0]
    if action == 'getData':
      return getData(start_response, params.get('week', ['0'])[0])
    elif isAdmin(environ) and action == 'saveTask':
      return saveTask(start_response, environ['wsgi.input'])
    elif isAdmin(environ) and action == 'removeTask':
      return removeTask(start_response, params.get('task', ['0'])[0])
    elif isAdmin(environ) and action == 'prioritizeTasks':
      return prioritizeTasks(start_response, environ['wsgi.input'])
    else:
      return error(start_response, 'Unsupported action')

  # Default response - main page
  template = get_template(get_config().get('tasks', 'mainPageTemplate'))
  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'isAdmin': isAdmin(environ)}).encode('utf-8')]

def getData(start_response, week):
  try:
    week = min(int(week), 0)
  except:
    week = 0
  anchorDate = date.today() + timedelta(weeks=week)
  weekDay = anchorDate.weekday()
  startDate = (anchorDate - timedelta(days=weekDay)).strftime('%Y-%m-%d')
  endDate = (anchorDate + timedelta(days=6-weekDay)).strftime('%Y-%m-%d')

  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  executeQuery(cursor,
               '''SELECT id, priority, description, context, status,
                         DATE_FORMAT(resolved, "%%Y-%%m-%%d") as resolved,
                         timespent
                  FROM #TABLE#
                  WHERE status = 2 AND resolved BETWEEN %s AND %s
                  ORDER BY resolved, priority''',
                  (startDate, endDate))
  data = {'week': week, 'startDate': startDate, 'endDate': endDate, 'tasks': cursor.fetchall()}

  if week == 0:
    executeQuery(cursor,
                 '''SELECT id, priority, description, context, status,
                         DATE_FORMAT(resolved, "%%Y-%%m-%%d") as resolved,
                           timespent
                    FROM #TABLE#
                    WHERE status <> 2
                    ORDER BY priority''', ())
    data['tasks'] += cursor.fetchall()

  start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
  return [json.dumps(data).encode('utf-8')]

def saveTask(start_response, inputStream):
  taskData = json.load(inputStream)
  cursor = get_db().cursor()
  if 'id' in taskData:
    executeQuery(cursor,
                 '''UPDATE #TABLE# SET description=%s, context=%s, status=%s,
                                       resolved=STR_TO_DATE(%s, "%%Y-%%m-%%d"),
                                       timespent=%s WHERE id=%s''',
                 (taskData['description'], taskData['context'], taskData['status'],
                  taskData['resolved'], taskData['timespent'], taskData['id']))
  else:
    executeQuery(cursor,
                 '''INSERT INTO #TABLE# (priority, description, context, status,
                                         created, resolved, timespent)
                    VALUES (%s, %s, %s, %s, NOW(), STR_TO_DATE(%s, "%%Y-%%m-%%d"), %s)''',
                 (taskData['priority'], taskData['description'], taskData['context'],
                  taskData['status'], taskData['resolved'], taskData['timespent']))
    taskData['id'] = get_db().insert_id()
  get_db().commit()
  start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
  return [json.dumps(taskData['id']).encode('utf-8')]

def removeTask(start_response, task):
  try:
    task = int(task)
  except:
    task = 0
  cursor = get_db().cursor()
  executeQuery(cursor, 'DELETE FROM #TABLE# WHERE id=%s', (task))
  get_db().commit()
  start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
  return []

def prioritizeTasks(start_response, inputStream):
  changes = json.load(inputStream)
  cursor = get_db().cursor()
  for change in changes:
    executeQuery(cursor, 'UPDATE #TABLE# SET priority=%s WHERE id=%s', (change['priority'], change['id']))
  get_db().commit()
  start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
  return []

@cached(600)
def get_db():
  database = get_config().get('tasks', 'database')
  dbuser = get_config().get('tasks', 'dbuser')
  dbpasswd = get_config().get('tasks', 'dbpassword')
  if os.name == 'nt':
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset='utf8', named_pipe=True)
  else:
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset='utf8')

def executeQuery(cursor, query, args=None):
  tableName = get_config().get('tasks', 'dbtable')
  query = re.sub(r'#TABLE#', tableName, query)
  cursor.execute(query, args)

def error(start_response, message):
  start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
  return [message]

def isAdmin(environ):
  return environ['REMOTE_ADDR'] == environ['SERVER_ADDR']
