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


import argparse
import io
import os
import sys
import json

from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

from sitescripts.oauth2dl.bin import constants as cnts


def download_file(url, key_file, scope):
    """Download a file using Oauth2.

    Parameters
    ----------
    url: str
        The url of the file we want to download
    key_file: str
        Path/ url to key file used in Oauth2
    scope: str
        The scope used in Oauth2

    Returns
    -------
    dict
        Headers resulted from the HTTP request.
    str
        Content of the file we want to download/ error message if unsuccessful.

    """
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_file,
        scopes=[scope],
    )

    http_auth = credentials.authorize(Http())

    headers, content = http_auth.request(url)
    try:
        content = content.decode('utf-8')
    finally:
        return headers, content


def parse_args():
    """Set up the required arguments and returns them."""
    parser = argparse.ArgumentParser(description='Download using Oauth2')

    parser.add_argument('url', help='URL to download from')
    parser.add_argument('-k', '--key', help='Oauth2 key file path',
                        default=os.environ.get('OAUTH2DL_KEY'))
    parser.add_argument('-s', '--scope', help='Oauth2 scope',
                        default=os.environ.get('OAUTH2DL_SCOPE'))
    parser.add_argument('-o', help='Path where to save the file.')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.key is None:
        sys.exit(cnts.KEYFILE_NOT_FOUND_ERROR)

    if args.scope is None:
        sys.exit(cnts.SCOPE_NOT_FOUND_ERROR)

    try:
        headers, content = download_file(args.url, args.key, args.scope)
    except KeyError as err:
        sys.exit(cnts.INVALID_KEY_FILE.format(str(err), str(args.key)))
    except Exception as err:
        sys.exit(err)

    if headers['status'] != '200':
        try:
            error_json = json.loads(content, encoding='utf-8')
            sys.exit(cnts.GOOGLE_OAUTH_ERROR.format(
                str(error_json['error']['code']),
                str(error_json['error']['message']),
            ))
        except ValueError:
            sys.exit(content)

    if args.o is None:
        sys.stdout.write(content)
    else:
        with io.open(args.o, encoding='utf-8', mode='wb') as f:
            f.write(content)


if __name__ == '__main__':
    main()
