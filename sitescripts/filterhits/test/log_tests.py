# coding: utf-8

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
import shutil
import time
import unittest

from sitescripts.filterhits.test import test_helpers
from sitescripts.filterhits.web import submit


class LogTestCase(test_helpers.FilterhitsTestCase):
    def test_log_filterhits(self):
        def list_files(d):
            return filter(os.path.isfile, [os.path.join(d, f) for f in os.listdir(d)])

        todays_date = time.strftime("%Y-%m-%d", time.gmtime())
        todays_folder = os.path.join(self.test_dir, todays_date)

        # The temporary logging directory is created at the start of all tests but
        # we want to test that the directory is created if it doesn't already exist.
        # So we'll delete the directory here and make sure it's re-created later on.
        shutil.rmtree(self.test_dir)
        self.assertEqual(os.path.exists(self.test_dir), False)

        log_file = submit.log_filterhits({"some": "thing"}, self.test_dir, "a=1")
        now = time.strftime("%d/%b/%Y:%H:%M:%S", time.gmtime())
        self.assertEqual(os.path.exists(self.test_dir), True)
        self.assertEqual(os.path.exists(todays_folder), True)
        self.assertEqual(len(list_files(todays_folder)), 1)
        self.assertEqual(os.path.exists(log_file), True)
        with open(list_files(todays_folder)[0], "r") as f:
            self.assertEqual(f.read(), '[%s] a=1\n{"some": "thing"}' % now)

        submit.log_filterhits({"some": "thing"}, self.test_dir, "")
        self.assertEqual(os.path.exists(self.test_dir), True)
        self.assertEqual(os.path.exists(todays_folder), True)
        self.assertEqual(len(list_files(todays_folder)), 2)

if __name__ == "__main__":
    unittest.main()
