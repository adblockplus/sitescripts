import MySQLdb, os
from sitescripts.utils import cached, get_config
from sitescripts.web import url_handler, basic_auth
from urlparse import parse_qsl

@cached(600)
def get_db():
  database = get_config().get("crawler", "database")
  dbuser = get_config().get("crawler", "dbuser")
  dbpasswd = get_config().get("crawler", "dbpassword")
  if os.name == "nt":
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset="utf8", named_pipe=True)
  else:
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset="utf8")

def get_cursor():
  return get_db().cursor(MySQLdb.cursors.DictCursor)

def fetch_crawlable_urls():
  cursor = get_cursor()
  cursor.execute("SELECT url from crawler_sites")
  results = cursor.fetchall()
  urls = [result["url"] for result in results]
  return urls

@url_handler("/crawlableUrls")
@basic_auth
def crawlable_urls(environ, start_response):
  urls = fetch_crawlable_urls()
  start_response("200 OK", [("Content-Type", "text/plain")])
  return "\n".join(urls)

@url_handler("/crawlerRun")
@basic_auth
def crawler_run(environ, start_response):
  cursor = get_cursor()
  cursor.execute("INSERT INTO crawler_runs () VALUES ()")
  start_response("200 OK", [("Content-Type", "text/plain")])
  return str(cursor.lastrowid)

def find_site_id(site_url):
  cursor = get_cursor()
  cursor.execute("SELECT id FROM crawler_sites WHERE url = %s", site_url)
  return cursor.fetchall()[0]["id"]

@url_handler("/crawlerData")
@basic_auth
def crawler_data(environ, start_response):
  params = dict(parse_qsl(environ["QUERY_STRING"]))
  run_id = params["run"]
  site_id = find_site_id(params["site"])
  url = params["url"]
  filtered = params["filtered"] == "true"
  cursor = get_cursor()
  cursor.execute("""
INSERT INTO crawler_data (run, site, url, filtered)
VALUES (%s, %s, %s, %s)""",
                 (run_id, site_id, url, filtered))
  start_response("200 OK", [("Content-Type", "text/plain")])
  return ""
