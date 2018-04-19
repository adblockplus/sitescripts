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

import glob
import hashlib
import json
import os
import re
from urlparse import parse_qs

from jinja2 import Template

from sitescripts.utils import get_config
from sitescripts.web import url_handler

_MANIFEST_TEMPLATE = Template('''<?xml version="1.0"?>
<updates>
{% if build %}
    <update buildID="{{ build.build_id }}">
        <patch
          URL="{{ build.url }}"
          hashFunction="{{ build.hash_function }}"
          hashValue="{{ build.hash_value }}"
          size="{{ build.size }}"/>
    </update>
{% endif %}
</updates>

''', autoescape=True)


def _get_latest_build(builds_dir):
    latest_build = {'id': 0}
    for json_path in glob.glob(os.path.join(builds_dir, 'adblockbrowser-*.json')):
        with open(json_path) as json_file:
            build_id = int(json.loads(json_file.read())['buildid'])
        if build_id > latest_build['id']:
            latest_build['id'] = build_id
            apk_path = os.path.splitext(json_path)[0] + '.apk'
            latest_build['path'] = os.path.join(builds_dir, apk_path)
    if latest_build['id'] == 0:
        return {}
    return latest_build


def _render_manifest(build=None, builds_url=None):
    if not build:
        return _MANIFEST_TEMPLATE.render()

    build_url = '%s/%s?update' % (builds_url, os.path.basename(build['path']))
    with open(build['path'], 'rb') as build_file:
        build_content = build_file.read()
    return _MANIFEST_TEMPLATE.render({
        'build': {
            'build_id': build['id'],
            'url': build_url,
            'hash_function': 'SHA512',
            'hash_value': hashlib.sha512(build_content).hexdigest(),
            'size': len(build_content),
        },
    })


def _get_update_manifest(current_build_id, builds_dir, builds_url):
    if not os.path.isdir(builds_dir):
        return _render_manifest()

    latest_build = _get_latest_build(builds_dir)
    if not latest_build or current_build_id >= latest_build['id']:
        return _render_manifest()
    return _render_manifest(latest_build, builds_url)


def _handle_request(environ, start_response, builds_dir, builds_url):
    params = parse_qs(environ.get('QUERY_STRING', ''))
    try:
        version = params.get('addonVersion', [''])[0]
        build_id = int(re.search(r'(\d+)$', version).group(1))
    except:
        start_response('400 Processing Error', [('Content-Type', 'text/plain')])
        return ['Failed to parse addonVersion.']
    manifest = _get_update_manifest(build_id, builds_dir, builds_url)
    response = manifest.encode('utf-8')
    start_response('200 OK', [('Content-Type', 'application/xml; charset=utf-8')])
    return [response]


@url_handler('/adblockbrowser/updates.xml')
def adblockbrowser_updates(environ, start_response):
    config = get_config()

    builds_dir = config.get('extensions', 'downloadsDirectory')
    builds_url = config.get('extensions', 'downloadsURL').rstrip('/')

    return _handle_request(environ, start_response, builds_dir, builds_url)


@url_handler('/devbuilds/adblockbrowser/updates.xml')
def adblockbrowser_devbuild_updates(environ, start_response):
    config = get_config()

    nightlies_dir = config.get('extensions', 'nightliesDirectory')
    builds_dir = os.path.join(nightlies_dir, 'adblockbrowser')

    nightlies_url = config.get('extensions', 'nightliesURL').rstrip('/')
    builds_url = '%s/adblockbrowser' % nightlies_url

    return _handle_request(environ, start_response, builds_dir, builds_url)
