# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2017 eyeo GmbH
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

import pytest

from sitescripts.utils import get_template


def test_get_template_default_path():
    """Load template from inside sitescripts."""
    template = get_template('__init__.py')
    assert template.render({}).startswith('# This file')


@pytest.mark.parametrize('mode', ['relative', 'absolute'])
def test_get_template(tmpdir, mode):
    """Load template using relative or absolute path."""
    template_path = tmpdir.join('template.tmpl')
    template_path.write('value = {{ value }}')

    if mode == 'absolute':
        template = get_template(template_path.strpath)
    else:
        template = get_template('template.tmpl', template_path=tmpdir.strpath)

    assert template.render({'value': 1}) == 'value = 1'
