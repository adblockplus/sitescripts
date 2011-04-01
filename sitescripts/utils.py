# coding: utf-8

import os, sys, codecs, subprocess, sitescripts
from time import time
from tempfile import mkstemp
from ConfigParser import SafeConfigParser

siteScriptsPath = sitescripts.__path__[0]

class cached(object):
  """
    Decorator that caches a function's return value for a given number of seconds.
    Note that this can only be used with functions that take no arguments.
  """

  def __init__(self, timeout):
    self.timeout = timeout
    self.func = None
    self.lastUpdate = None
    self.lastResult = None

  def __call__(self, *args):
    if len(args) == 1:
      # We got called with the function to be decorated - remember the function
      # and return the same object again
      self.func = args[0]
      return self
    else:
      currentTime = time()
      if self.lastUpdate == None or currentTime - self.lastUpdate > self.timeout:
        self.lastResult = self.func()
        self.lastUpdate = currentTime
      return self.lastResult

  def __repr__(self):
    """Return the function's docstring"""
    return self.func.__doc__

@cached(3600)
def get_config():
  """
    Returns parsed configuration file (SafeConfigParser instance). File paths
    that will be checked: ~/.sitescripts, ~/sitescripts.ini, /etc/sitescripts,
    /etc/sitescripts.ini
  """

  paths = []

  # For debugging - accept configuration in user's profile
  paths.append(os.path.expanduser('~/.sitescripts'))
  paths.append(os.path.expanduser('~/sitescripts.ini'))

  # Server-wide configuration if no custom found
  paths.append(os.path.expanduser('/etc/sitescripts'))
  paths.append(os.path.expanduser('/etc/sitescripts.ini'))

  for path in paths:
    path = os.path.abspath(path)
    if os.path.exists(path):
      config = SafeConfigParser()
      config.read(path)
      return config

  raise Exception('No config file found. Please put sitescripts.ini into your home directory or /etc')

def setupStderr(stream=sys.stderr):
  """
    Sets up sys.stderr to accept Unicode characters, redirects error output to
    the stream passed in if any.
  """
  sys.stderr = codecs.getwriter('utf8')(stream)

def sendMail(template, data):
  """
    Sends a mail generated from the template and data given.
  """
  template = get_template(template, False)
  mail = template.render(data)
  if get_config().get('DEFAULT', 'mailerDebug') == 'yes':
    (handle, path) = mkstemp(prefix='mail_', suffix='.eml', dir='.')
    os.close(handle)
    f = codecs.open(path, 'wb', encoding='utf-8')
    print >>f, mail
    f.close()
  else:
    subprocess.Popen([get_config().get('DEFAULT', 'mailer'), '-t'], stdin=subprocess.PIPE).communicate(mail.encode('utf-8'))

_template_cache = {}

def get_template(template, autoescape=True):
  """Parses and returns a Jinja2 template"""
  key = (template, autoescape)
  if not key in _template_cache:
    if autoescape:
      env = get_template_environment()
    else:
      env = get_unescaped_template_environment()
    _template_cache[key] = env.get_template(template)
  return _template_cache[key]

@cached(())
def get_template_environment():
  """
    Returns a Jinja2 template environment with autoescaping enabled.
  """
  from sitescripts.templateFilters import filters
  import jinja2
  env = jinja2.Environment(loader=jinja2.FileSystemLoader(siteScriptsPath), autoescape=True, extensions=['jinja2.ext.autoescape'])
  env.filters.update(filters)
  return env

@cached(())
def get_unescaped_template_environment():
  """
    Returns a Jinja2 template environment without autoescaping. Don't use this to
    generate HTML files!
  """
  from sitescripts.templateFilters import filters
  import jinja2
  env = jinja2.Environment(loader=jinja2.FileSystemLoader(siteScriptsPath))
  env.filters.update(filters)
  return env
