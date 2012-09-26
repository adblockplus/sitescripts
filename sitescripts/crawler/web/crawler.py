import MySQLdb, os, simplejson, sys
from sitescripts.utils import cached, get_config
from sitescripts.web import url_handler, basic_auth

@cached(600)
def _get_db():
  database = get_config().get("crawler", "database")
  dbuser = get_config().get("crawler", "dbuser")
  dbpasswd = get_config().get("crawler", "dbpassword")
  if os.name == "nt":
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                           use_unicode=True, charset="utf8", named_pipe=True)
  else:
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database,
                           use_unicode=True, charset="utf8")

def get_cursor():
  return _get_db().cursor(MySQLdb.cursors.DictCursor)

def _fetch_crawlable_sites():
  cursor = get_cursor()
  cursor.execute("SELECT url from crawler_sites")
  results = cursor.fetchall()
  sites = [result["url"] for result in results]
  return sites

@url_handler("/crawlableSites")
@basic_auth
def crawlable_sites(environ, start_response):
  urls = _fetch_crawlable_sites()
  start_response("200 OK", [("Content-Type", "text/plain")])
  return "\n".join(urls)

def _find_site_id(site_url):
  cursor = get_cursor()
  cursor.execute("SELECT id FROM crawler_sites WHERE url = %s", site_url)
  result = cursor.fetchone()
  return result["id"] if result else None

def _read_multipart_lines(environ, line_callback):
  data_file = environ["wsgi.input"]
  current_line = 0

  while True:
    line = data_file.readline().strip()
    current_line += 1

    if current_line == 1:
      boundary = line
      continue

    if current_line < 5 or not line:
      continue

    if line.startswith(boundary):
      break

    line_callback(line)

def _create_run():
  cursor = get_cursor()
  cursor.execute("INSERT INTO crawler_runs () VALUES ()")
  return cursor.lastrowid

def _insert_data(run_id, site, url, filtered):
  site_id = _find_site_id(site)
  if site_id is None:
    print >>sys.stderr, "Unable to find site '%s' in the database" % site
    return

  cursor = get_cursor()
  cursor.execute("""
INSERT INTO crawler_data (run, site, url, filtered)
VALUES (%s, %s, %s, %s)""",
                 (run_id, site_id, url, filtered))

@url_handler("/crawlerData")
@basic_auth
def crawler_data(environ, start_response):
  def line_callback(line):
    url, site, filtered = simplejson.loads(line)
    _insert_data(run_id, site, url, filtered)

  run_id = _create_run()
  _read_multipart_lines(environ, line_callback)
  start_response("200 OK", [("Content-Type", "text/plain")])
  return ""
