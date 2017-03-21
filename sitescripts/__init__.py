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

# If connected to a terminal, show all warnings. By default (since Python 2.7)
# deprecation warnings are ignored, because they are not of interest of users.
# However, everybody potentially running these scripts in a terminal is working
# on them and should be aware of all warnings.
import sys
if sys.stderr.isatty():
    import warnings
    warnings.simplefilter('default')
