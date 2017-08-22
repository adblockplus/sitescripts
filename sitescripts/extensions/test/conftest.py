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

"""
Contains fixtures that are useful across test scripts for the extensions module
"""

import subprocess

import pytest
import py


@pytest.fixture(scope='session')
def tests_dir():
    """Directory that contains this tests and the data files it uses."""
    return py.path.local(__file__).dirpath()


@pytest.fixture(scope='session')
def data_dir(tests_dir):
    return tests_dir.join('data')


@pytest.fixture(scope='session')
def diff_dir(data_dir):
    return data_dir.join('diff')


@pytest.fixture(scope='session')
def keys_dir(tmpdir_factory, tests_dir):
    keys_dir = tmpdir_factory.mktemp('keys')
    key_filename = 'adblockplussafari.pem'
    tests_dir.join(key_filename).copy(keys_dir.join(key_filename))
    return keys_dir


def call_hg(cwd, *params):
    return subprocess.check_call(['hg'] + list(params), cwd=str(cwd))


def hg_import(repo_dir, diff_dir):
    call_hg(repo_dir, 'import', diff_dir.strpath, '--exact')


@pytest.fixture(scope='session')
def hg_dir(tmpdir_factory, data_dir, diff_dir):
    """Directory that contains the repository mocks."""
    hg_dir = tmpdir_factory.mktemp('hg')

    # Mock repositories from diff and bookmarks.
    for diff in diff_dir.visit():
        repo_name = diff.purebasename.split('.')[0]
        repo_dir = hg_dir.mkdir(repo_name)
        call_hg(repo_dir, 'init')
        bookmark_file = data_dir.join('bookmarks', repo_name + '.bookmarks')
        if bookmark_file.exists():
            destination = repo_dir.join('.hg').join('bookmarks')
            bookmark_file.copy(destination)
        hg_import(repo_dir, diff)

    return hg_dir


@pytest.fixture()
def config_ini(tests_dir, tmpdir, hg_dir, keys_dir):
    """Sitescripts configuration."""
    template = tests_dir.join('sitescripts.ini.template').read()
    conf = template.format(hg_dir=hg_dir, out_dir=tmpdir, keys_dir=keys_dir)
    config_ini = tmpdir.join('sitescripts.ini')
    config_ini.write(conf)
    return config_ini
