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

KEYFILE_NOT_FOUND_ERROR = (
    'ERROR: Oauth2 key file not found! Please specify it as an optional '
    'argument using -k or --key or add it to the environment variable '
    'OAUTH2DL_KEY.'
)

SCOPE_NOT_FOUND_ERROR = (
    'ERROR: Oauth2 scope not found! Please specify it as an optional argument '
    'using -s or --scope or add it to the environment variable OAUTH2DL_SCOPE'
)

INVALID_KEY_FILE = 'ERROR: Invalid key file format! {0} not found in {1}!'

DUMMY_PRIVATE_KEY = (
    '-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK8Q+ToR4tWGshaKYRHKJ3ZmMUF6'
    'jjwCS/u1A8v1tFbQiVpBlxYB\npaNcT2ENEXBGdmWqr8VwSl0NBIKyq4p0rhsCAQMCQHS1+3w'
    'L7I5ZzA8G62Exb6RE\nINZRtCgBh/0jV91OeDnfQUc07SE6vs31J8m7qw/rxeB3E9h6oGi9I'
    'VRebVO+9zsC\nIQDWb//KAzrSOo0P0yktnY57UF9Q3Y26rulWI6LqpsxZDwIhAND/cmlg7rUz'
    '34Pf\nSmM61lJEmMEjKp8RB/xgghzmCeI1AiEAjvVVMVd8jCcItTdwyRO0UjWU4JOz0cnw\n5'
    'BfB8cSIO18CIQCLVPbw60nOIpUClNxCJzmMLbsrbMcUtgVS6wFomVvsIwIhAK+A\nYqT6WwsM'
    'W2On5l9di+RPzhDT1QdGyTI5eFNS+GxY\n-----END RSA PRIVATE KEY-----'
)

GOOGLE_OAUTH_ERROR = 'ERROR {0} - {1}'
