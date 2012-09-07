import MySQLdb, os
from sitescripts.utils import cached, get_config
from sitescripts.web import url_handler

@cached(600)
def get_db():
  database = get_config().get("crawler", "database")
  dbuser = get_config().get("crawler", "dbuser")
  dbpasswd = get_config().get("crawler", "dbpassword")
  if os.name == "nt":
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset="utf8", named_pipe=True)
  else:
    return MySQLdb.connect(user=dbuser, passwd=dbpasswd, db=database, use_unicode=True, charset="utf8")

def execute_query(cursor, query, args=None):
  cursor.execute(query, args)

def fetch_crawlable_urls():
  cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
  execute_query(cursor, "SELECT url from crawler_urls")
  results = cursor.fetchall()
  urls = [result["url"] for result in results]
  return urls

@url_handler("/crawlableUrls")
def crawlable_urls(environ, start_response):
  urls = fetch_crawlable_urls()
  start_response("200 OK", [("Content-Type", "text/plain")])
  return "\n".join(urls)
