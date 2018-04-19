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

from sitescripts.utils import get_config, sendMail, encode_email_address
from sitescripts.web import url_handler, form_handler, send_simple_response


@url_handler('/sendInstallationLink')
@form_handler
def send_installation_link(environ, start_response, data):
    email = data.get('email', '').strip()
    try:
        email = encode_email_address(email)
    except ValueError:
        return send_simple_response(
            start_response, 400,
            'Please enter a valid email address.',
        )

    config = get_config()
    template_path = config.get('send_installation_link', 'email_template')
    sendMail(template_path, {'recipient': email})

    return send_simple_response(
        start_response, 200,
        'The app is on the way! '
        'Please check your email on your smartphone or tablet.',
    )
