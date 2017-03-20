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

import datetime
import collections

from sitescripts.utils import (get_config, sendMail, encode_email_address,
                               get_template)
from sitescripts.web import registerUrlHandler, form_handler


def get_config_items():
    config = get_config()
    default_keys = set(config.defaults())
    for name, value in config.items('formmail2'):
        if name not in default_keys:
            yield name, value


def store_value(conf_dict, path, value):
    head, tail = path[0], path[1:]
    if head not in conf_dict:
        conf_dict[head] = collections.OrderedDict()
    if tail:
        store_value(conf_dict[head], tail, value)
    else:
        conf_dict[head].value = value


def conf_parse(conf_items):
    conf_dict = collections.OrderedDict()
    for key, value in conf_items:
        path = key.split('.')
        store_value(conf_dict, path, value)
    return conf_dict


def make_error(spec, check_type, default_message):
    if check_type in spec:
        return spec[check_type].value
    return default_message


def make_handler(name, config):
    try:
        url = config['url'].value
    except (KeyError, AttributeError):
        raise Exception('No URL configured for form handler: ' + name)
    try:
        template = config['template'].value
        get_template(template, autoescape=False)
    except (KeyError, AttributeError):
        raise Exception('No template configured for form handler: ' + name)
    try:
        fields = config['fields']
        for field, spec in fields.items():
            spec.value = {s.strip() for s in spec.value.split(',')}
    except KeyError:
        raise Exception('No fields configured for form handler: ' + name)
    if len(fields) == 0:
        raise Exception('No fields configured for form handler: ' + name)

    @form_handler
    def handler(environ, start_response, params):
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        errors = []
        for field, spec in fields.items():
            if 'mandatory' in spec.value:
                if field not in params.keys():
                    errors.append(make_error(spec, 'mandatory',
                                             'No {} entered'.format(field)))
            if 'email' in spec.value and field in params.keys():
                try:
                    params[field] = encode_email_address(params[field])
                except ValueError:
                    errors.append(make_error(spec, 'email', 'Invalid email'))
        if errors:
            start_response('400 Bad Request', response_headers)
            return '\n'.join(errors)

        template_args = {
            'time': datetime.datetime.now(),
            'fields': {field: params.get(field, '') for field in fields}
        }
        sendMail(template, template_args)
        start_response('200 OK', response_headers)
        return ''

    return url, handler


conf_dict = conf_parse(get_config_items())
for name, config in conf_dict.items():
    url, handler = make_handler(name, config)
    registerUrlHandler(url, handler)
