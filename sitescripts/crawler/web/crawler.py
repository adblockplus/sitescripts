import MySQLdb, os
from sitescripts.utils import cached, get_config
from sitescripts.web import url_handler
from urlparse import parse_qs

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

def execute_query(cursor, query, args=None):
  cursor.execute(query, args)

def fetch_crawlable_urls():
  cursor = get_cursor()
  execute_query(cursor, "SELECT url from crawler_sites")
  results = cursor.fetchall()
  urls = [result["url"] for result in results]
  return urls

@url_handler("/crawlableUrls")
def crawlable_urls(environ, start_response):
  urls = fetch_crawlable_urls()
  start_response("200 OK", [("Content-Type", "text/plain")])
  return "\n".join(urls)

@url_handler("/crawlerRun")
def crawler_run(environ, start_response):
  cursor = get_cursor()
  execute_query(cursor, "INSERT INTO crawler_runs () VALUES ()")
  return str(cursor.lastrowid)

def find_site_id(site_url):
  cursor = get_cursor()
  execute_query(cursor, "SELECT id FROM crawler_sites WHERE url = %s", site_url)
  return cursor.fetchall()[0]["id"]

@url_handler("/crawlerData")
def crawler_data(environ, start_response):
  params = parse_qs(environ["QUERY_STRING"])
  run_id = params["run"][0]
  site_id = find_site_id(params["site"][0])
  request_url = params["request_url"][0]
  document_url = params["document_url"][0]
  cursor = get_cursor()
  execute_query(cursor, """
INSERT INTO crawler_data (run, site, request_url, document_url)
VALUES (%s, %s, %s, %s)""",
                (run_id, site_id, request_url, document_url))
  start_response("200 OK", [("Content-Type", "text/plain")])
  return ""
