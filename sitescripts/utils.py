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
import sys
import re
import codecs
import subprocess
import sitescripts
from time import time
from tempfile import mkstemp
from ConfigParser import SafeConfigParser

siteScriptsPath = sitescripts.__path__[0]


class cached(object):
    """
      Decorator that caches a function's return value for a given number of seconds.
      Note that this only works if the string representation of the parameters is
      always unique.
    """

    def __init__(self, timeout):
        self.timeout = timeout
        self.lastResult = {}
        self.lastUpdate = {}

    def __call__(self, func):
        def wrapped(*args, **kwargs):
            key = str(kwargs)
            currentTime = time()
            if (args, key) not in self.lastUpdate or currentTime - self.lastUpdate[args, key] > self.timeout:
                self.lastResult[args, key] = func(*args, **kwargs)
                self.lastUpdate[args, key] = currentTime
            return self.lastResult[args, key]
        self.func = func
        return wrapped

    def __repr__(self):
        return repr(self.func)


@cached(3600)
def get_config():
    """
      Returns parsed configuration file (SafeConfigParser instance). File paths
      that will be checked: ~/.sitescripts, ~/sitescripts.ini, /etc/sitescripts,
      /etc/sitescripts.ini
    """

    paths = []

    # Allow SITESCRIPTS_CONFIG variable to override config path
    if 'SITESCRIPTS_CONFIG' in os.environ:
        paths.append(os.environ['SITESCRIPTS_CONFIG'])

    # For debugging - accept configuration in user's profile
    paths.append(os.path.expanduser('~/.sitescripts'))
    paths.append(os.path.expanduser('~/sitescripts.ini'))

    # Server-wide configuration if no custom found
    paths.append('/etc/sitescripts')
    paths.append('/etc/sitescripts.ini')

    for path in paths:
        path = os.path.abspath(path)
        if os.path.exists(path):
            config = SafeConfigParser()
            config.optionxform = lambda x: x
            config.read(path)
            return config

    raise Exception('No config file found. Please put sitescripts.ini into your home directory or /etc')


def setupStderr(stream=sys.stderr):
    """
      Sets up sys.stderr to accept Unicode characters, redirects error output to
      the stream passed in if any. DEPRECATED
    """
    import warnings
    warnings.warn('setupStderr() is deprecated. If you write '
                  'text to stderr that might be non-ASCII use '
                  'the "logging" module instead.', DeprecationWarning, 2)

    sys.stderr = codecs.getwriter('utf8')(stream)


def anonymizeMail(email):
    """
      Anonymizes email to look like a**.n***@g****.c**
    """
    return re.sub(r'(?<=[^.@])[^.@]', '*', email)


def sendMail(template, data):
    """
      Sends a mail generated from the template and data given.
    """
    template = get_template(template, False)
    mail = template.render(data)
    config = get_config()
    if config.has_option('DEFAULT', 'mailerDebug') and config.get('DEFAULT', 'mailerDebug') == 'yes':
        handle, path = mkstemp(prefix='mail_', suffix='.eml', dir='.')
        os.close(handle)
        f = codecs.open(path, 'wb', encoding='utf-8')
        print >>f, mail
        f.close()
    else:
        subprocess.Popen([config.get('DEFAULT', 'mailer'), '-t'], stdin=subprocess.PIPE).communicate(mail.encode('utf-8'))


def encode_email_address(email):
    """
    Validates and encodes an email address.

    The validation implemented here is very rudamentery and not meant
    to be complete, as full email validation can get extremly complicated
    and is rarely needed. This function is primarily making sure that the
    email address contains no whitespaces and only valid ASCII characters.
    """
    match = re.search(r'^([^@\s]+)@([^@\s]+)$', email)
    if not match:
        raise ValueError

    try:
        return email.encode('ascii')
    except UnicodeEncodeError:
        return '%s@%s' % (match.group(1).encode('ascii'),
                          match.group(2).encode('idna'))


_template_cache = {}


def get_template(template, autoescape=True, template_path=siteScriptsPath):
    """Load Jinja2 template.

    If `template` is a relative path, it's looked up inside `template_path`.
    If it's an absolute path, `template_path` is not used.

    Note: Each template will only be loaded once (when first requested). After
    that it will be cached and reused -- any changes on the filesystem will be
    ignored.
    """
    if os.path.isabs(template):
        template_path, template = os.path.split(template)
    template_path = os.path.abspath(template_path)
    key = (template_path, template, autoescape)
    if key not in _template_cache:
        if autoescape:
            env = get_template_environment(template_path)
        else:
            env = get_unescaped_template_environment(template_path)
        _template_cache[key] = env.get_template(template)
    return _template_cache[key]


@cached(float('inf'))
def get_template_environment(template_path):
    """
      Returns a Jinja2 template environment with autoescaping enabled.
    """
    from sitescripts.templateFilters import filters
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path),
                             autoescape=True)
    env.filters.update(filters)
    return env


@cached(float('inf'))
def get_unescaped_template_environment(template_path):
    """
      Returns a Jinja2 template environment without autoescaping. Don't use this to
      generate HTML files!
    """
    from sitescripts.templateFilters import filters
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
    env.filters.update(filters)
    return env


def get_custom_template_environment(additional_filters, loader=None):
    """
      Returns a custom Jinja2 template environment with additional filters.
    """
    from sitescripts.templateFilters import filters
    import jinja2
    if not loader:
        loader = jinja2.FileSystemLoader(siteScriptsPath)
    env = jinja2.Environment(loader=loader, autoescape=True)
    env.filters.update(filters)
    env.filters.update(additional_filters)
    return env
