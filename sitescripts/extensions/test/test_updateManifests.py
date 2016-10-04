# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

"""Tests for update manifest generation script."""

import json
import os
import subprocess
import xml.etree.ElementTree as ET

import pytest
import py


@pytest.fixture()
def tests_dir():
    """Directory that contains this tests and the data files it uses."""
    return py.path.local(__file__).dirpath()


@pytest.fixture()
def oracle(tests_dir):
    """Function that returns expected content of generated files."""
    def expected_value_of(what):
        return tests_dir.join('oracle').join(what).read().strip()
    return expected_value_of


@pytest.fixture()
def data_dir(tests_dir):
    return tests_dir.join('data')


@pytest.fixture()
def keys_dir(tmpdir, tests_dir):
    keys_dir = tmpdir.mkdir('keys')
    key_filename = 'adblockplussafari.pem'
    tests_dir.join(key_filename).copy(keys_dir.join(key_filename))
    return keys_dir


def call_hg(cwd, *params):
    return subprocess.check_call(['hg'] + list(params), cwd=str(cwd))


REPOS = {
    'adblockplus': ('metadata.gecko', '2.7.3'),
    'adblockplusie': ('README.txt', '1.33.7'),
    'adblockpluschrome': ('metadata.safari', '1.12.3'),
    'adblockplusandroid': ('AndroidManifest.xml', '1.3')
}


@pytest.fixture()
def hg_dir(tmpdir, data_dir):
    """Directory that contains the repository mocks."""
    hg_dir = tmpdir.mkdir('hg')

    # Mock plugin repositories.
    for repo, config in REPOS.items():
        filename, tag = config
        repo_dir = hg_dir.mkdir(repo)
        call_hg(repo_dir, 'init')
        data_dir.join(filename).copy(repo_dir.join(filename))
        call_hg(repo_dir, 'add', filename)
        call_hg(repo_dir, 'commit', '-m', '1')
        call_hg(repo_dir, 'tag', tag)

    # Mock the downloads repository.
    downloads_list = data_dir.join('downloads.list').read().splitlines()
    downloads_dir = hg_dir.mkdir('downloads')
    call_hg(downloads_dir, 'init')
    for item in downloads_list:
        downloads_dir.join(item).write('')
    call_hg(downloads_dir, 'add', *downloads_list)
    call_hg(downloads_dir, 'commit', '-m', 'ok')

    return hg_dir


@pytest.fixture()
def config_ini(tests_dir, tmpdir, hg_dir, keys_dir):
    """Sitescripts configuration."""
    template = tests_dir.join('sitescripts.ini.template').read()
    conf = template.format(hg_dir=hg_dir, out_dir=tmpdir, keys_dir=keys_dir)
    config_ini = tmpdir.join('sitescripts.ini')
    config_ini.write(conf)
    return config_ini


def rdf2data(rdf):
    """Convert RDF to a more comparable data strcuture."""
    # We need this to address the RDF item ordering discrepancies.
    def et2data(node):
        return {
            'tag': node.tag,
            'text': node.text,
            'attrib': node.attrib,
            'subs': sorted(et2data(sub) for sub in node)
        }
    return et2data(ET.fromstring(rdf))


def test_update_manifests(config_ini, hg_dir, tmpdir, oracle):
    env = dict(os.environ)
    env['SITESCRIPTS_CONFIG'] = str(config_ini)
    cmd = ['python', '-m', 'sitescripts.extensions.bin.updateUpdateManifests']
    subprocess.check_call(cmd, env=env)
    for filename in ['androidupdates.json', 'androidupdates.xml',
                     'ieupdate.json', 'update.rdf', 'updates.plist']:
        got = tmpdir.join(filename).read().strip()
        expect = oracle(filename)
        if filename.endswith('.json'):
            got = json.loads(got)
            expect = json.loads(expect)
        elif filename.endswith('.rdf'):
            got = rdf2data(got)
            expect = rdf2data(expect)
        assert got == expect
