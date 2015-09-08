# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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

import sys
import argparse
import logging

from sitescripts.utils import get_template, sendMail

parser = argparse.ArgumentParser(description='Renders the given email template '
                                             'and dispatches emails to the '
                                             'addresses given on stdin')
parser.add_argument('template')
parser.add_argument('--log-level', default='INFO')

if __name__ == '__main__':
  args = parser.parse_args()
  logging.basicConfig(level=args.log_level)
  template = get_template(args.template, False)

  for recipient in sys.stdin:
    recipient = recipient.strip()
    try:
      sendMail(template, {'recipient': recipient})
    except Exception:
      logging.error('Failed to send email to %r', recipient, exc_info=True)
    else:
      logging.info('Sent email to %r', recipient)
