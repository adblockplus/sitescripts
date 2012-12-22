import MySQLdb, os, re, simplejson, sys
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

def _get_cursor():
  return _get_db().cursor(MySQLdb.cursors.DictCursor)

def _fetch_crawlable_sites():
  cursor = _get_cursor()
  cursor.execute("SELECT url from crawler_sites")
  results = cursor.fetchall()
  sites = [result["url"] for result in results]
  return sites

@url_handler("/crawlableSites")
@basic_auth("crawler")
def crawlable_sites(environ, start_response):
  urls = _fetch_crawlable_sites()
  start_response("200 OK", [("Content-Type", "text/plain")])
  return "\n".join(urls)

def _find_site_id(site_url):
  cursor = _get_cursor()
  cursor.execute("SELECT id FROM crawler_sites WHERE url = %s", site_url)
  result = cursor.fetchone()
  return result["id"] if result else None

def _read_multipart_lines(environ, line_callback):
  data_file = environ["wsgi.input"]
  content_type = environ.get("CONTENT_TYPE")
  if not content_type:
    raise ValueError("Content-Type missing from header")

  match = re.search(r"boundary=(.*)", content_type)
  if not match:
    raise ValueError("Multipart form data or boundary declaration missing")

  boundary = match.group(1)
  boundary_passed = False
  header_passed = False

  for line in data_file:
    line = line.strip()

    if not boundary_passed:
      if line == "--" + boundary:
        boundary_passed = True
      continue

    if not header_passed:
      if not line:
        header_passed = True
      continue

    if line == "--" + boundary + "--":
      break

    if line:
      line_callback(line)

def _create_run():
  cursor = _get_cursor()
  cursor.execute("INSERT INTO crawler_runs () VALUES ()")
  return cursor.lastrowid

def _insert_data(run_id, site, url, filtered):
  site_id = _find_site_id(site)
  if site_id is None:
    print >>sys.stderr, "Unable to find site '%s' in the database" % site
    return

  cursor = _get_cursor()
  cursor.execute("""
INSERT INTO crawler_data (run, site, url, filtered)
VALUES (%s, %s, %s, %s)""",
                 (run_id, site_id, url, filtered))

@url_handler("/crawlerData")
@basic_auth("crawler")
def crawler_data(environ, start_response):
  def line_callback(line):
    try:
      data = simplejson.loads(line)
      if len(data) < 3:
        print >>sys.stderr, "Not enough elements in line '%s'" % line
        return
      url = data[0]
      site = data[1]
      filtered = data[2]
      _insert_data(run_id, site, url, filtered)
    except simplejson.JSONDecodeError:
      print >>sys.stderr, "Unable to parse JSON from '%s'" % line

  run_id = _create_run()
  try:
    _read_multipart_lines(environ, line_callback)
    start_response("200 OK", [("Content-Type", "text/plain")])
    return ""
  except ValueError as e:
    start_response("401 Bad Request", [("Content-Type", "text/plain")])
    print >>sys.stderr, "Unable to read multipart data: %s" % e
    return e
