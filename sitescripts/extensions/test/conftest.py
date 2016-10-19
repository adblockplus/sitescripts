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

"""
Contains fixtures that are useful across test scripts for the extensions module
"""

import subprocess

import pytest
import py

REPOS = {
    'adblockplus': ('metadata.gecko', '2.7.3'),
    'adblockplusie': ('README.txt', '1.33.7'),
    'adblockpluschrome': ('metadata.safari', '1.12.3'),
    'adblockplusandroid': ('AndroidManifest.xml', '1.3'),
    'adblockplusnightly': ('README.txt', '0.0')
}


@pytest.fixture(scope='session')
def tests_dir():
    """Directory that contains this tests and the data files it uses."""
    return py.path.local(__file__).dirpath()


@pytest.fixture(scope='session')
def data_dir(tests_dir):
    return tests_dir.join('data')


# Fixtures using the built in tmpdir fixture must be function scoped which
# causes about a 30% slow down. It would be faster to use tmpdir_factory
# which is session scoped but for no it is not important.
@pytest.fixture()
def keys_dir(tmpdir, tests_dir):
    keys_dir = tmpdir.mkdir('keys')
    key_filename = 'adblockplussafari.pem'
    tests_dir.join(key_filename).copy(keys_dir.join(key_filename))
    return keys_dir


def call_hg(cwd, *params):
    return subprocess.check_call(['hg'] + list(params), cwd=str(cwd))


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

    call_hg(hg_dir.join('adblockplusnightly'), 'bookmark', 'safari')

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
