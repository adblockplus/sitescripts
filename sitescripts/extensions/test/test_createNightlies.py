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

import os
from subprocess import CalledProcessError

import pytest

from sitescripts.extensions.bin import createNightlies
from sitescripts.utils import get_config


@pytest.fixture(scope='session')
def nightlydir(hg_dir):
    return hg_dir.join('adblockplusnightly')


@pytest.fixture(scope='session')
def config(hg_dir, nightlydir):
    """Set and return config obj for NightlyBuild"""
    config = get_config()
    config.type = 'safari'
    config.revision = 'safari'
    config.repositoryName = 'adblockplusnightly'
    config.repository = nightlydir.strpath
    return config


@pytest.fixture(scope='session')
def nightlybuild(config):
    return createNightlies.NightlyBuild(config)


def test_nightly_object_bookmark(nightlybuild):
    assert nightlybuild.config.revision == 'safari'


def test_current_revision(nightlybuild):
    # The hash is the commit that the safari bookmark points to.
    # (see adblockplusnightly.bookmark in test/data/bookmarks)
    assert nightlybuild.revision == '1291590ddd0f'


def test_copy_repository(nightlybuild, nightlydir):
    nightlybuild.copyRepository()
    files = os.listdir(nightlybuild.tempdir)
    assert set(files) == {'.hg', 'README.txt'}


def test_get_changes(nightlybuild, nightlydir):
    # The bookmark 'safari' contains only 2 revisions
    # default contains 51 so here we ensure that erroneous changes
    # are not returned
    for change in nightlybuild.getChanges():
        assert change['revision'] < '2'

    nightlybuild.config.revision = 'default'
    for change in nightlybuild.getChanges():
        assert change['revision'] > '1'


def test_missing_bookmark(config):
    config.revision = 'foo'
    config.type = 'type'
    try:
        createNightlies.NightlyBuild(config)
    except CalledProcessError as e:
        assert e.returncode == 255
