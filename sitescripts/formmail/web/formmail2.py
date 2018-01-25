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

from __future__ import print_function

import os
import sys
import datetime
import traceback
import collections
from csv import DictWriter, DictReader

import jinja2

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


def log_formfield_error(parameters, log_path):
    err_file = os.path.basename(log_path) + '_error'
    err_path = os.path.join(os.path.dirname(log_path), err_file)
    if os.path.isfile(err_path):
        with open(err_path, 'a') as error_log:
            writer = DictWriter(error_log, fieldnames=parameters.keys())
            writer.writerow(parameters)
        raise Exception('Field names have changed, error log '
                        'appended to ' + err_path)
    with open(err_path, 'w') as error_log:
        writer = DictWriter(error_log, fieldnames=parameters.keys())
        writer.writeheader()
        writer.writerow(parameters)
    raise Exception('Field names have changed, error log '
                    'written to ' + err_path)


def log_formdata(params, path):
    if os.path.isfile(path):
        with open(path, 'ab+') as formlog:
            formlog.seek(0)
            reader = DictReader(formlog)
            if reader.fieldnames != params.keys():
                log_formfield_error(params, path)
            formlog.seek(os.SEEK_END)
            writer = DictWriter(formlog, fieldnames=params.keys())
            writer.writerow(params)
        return
    with open(path, 'w') as new_formlog:
        writer = DictWriter(new_formlog, fieldnames=params.keys())
        writer.writeheader()
        writer.writerow(params)
    return


def validate_fields(fields, params):
    errors = []
    for field, spec in fields.items():
        if 'mandatory' in spec.value and field not in params:
                errors.append(make_error(spec, 'mandatory',
                                         'No {} entered'.format(field)))
        if 'email' in spec.value and field in params:
            try:
                params[field] = encode_email_address(params[field])
            except ValueError:
                errors.append(make_error(spec, 'email', 'Invalid email'))

    unexpected_fields = ' '.join(set(params.keys()) - set(fields.keys()))
    if unexpected_fields:
        errors.append('Unexpected field/fields: ' + str(unexpected_fields))
    return errors


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
    except jinja2.TemplateNotFound:
        raise Exception('Template not found at: ' + template)
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
        errors = validate_fields(fields, params)
        if errors:
            start_response('400 Bad Request', response_headers)
            return '\n'.join(errors)
        time = datetime.datetime.now()
        template_args = {
            'time': time,
            'fields': {field: params.get(field, '') for field in fields}
        }
        try:
            sendMail(template, template_args)
        except:
            print(traceback.print_exc(), file=sys.stderr)
            start_response('500 Server Error', response_headers)
            return ''
        finally:
            if 'csv_log' in config:
                params = {field: params.get(field, '').encode('utf8')
                          for field in fields}
                params['time'] = time
                log_formdata(params, config['csv_log'].value)
        start_response('200 OK', response_headers)
        return ''

    return url, handler


conf_dict = conf_parse(get_config_items())
for name, config in conf_dict.items():
    url, handler = make_handler(name, config)
    registerUrlHandler(url, handler)
