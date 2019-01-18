# formmail

The web handler that extracts form data from a POST request, uses it to
populate an email template and then sends the produced email to a configured
list of addresses.

## Dependencies

* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [Jinja2](http://jinja.pocoo.org/docs/2.10/intro/)
* Other packages are required for testing, please see the list of 'deps' in
  [`tox.ini`](../../tox.ini)

## Running the web handler

Normally, the formmail web handler is run by the multiplexer, and configured
via the sitescripts config file. Please refer to the main
[README](../../README.md) for more information about the multiplexer and
configuring `sitescripts.ini`.

In order to activate this handler, add the following line to the multiplexer
config file:

    [multiplexer]
    sitescripts.formmail.web.formmail =

## Configuring the web handler

`formmail.py` can handle multiple URLs and forms. Each URL will correspond to a
group of config variables that all start with the same prefix, for example:
handler1. These variables are configured in the [formmail] section of the
config file.

The URL of the form, where the POST request comes from:

    [formmail]
    handler1.url = formmail/test/apply/submit

The CSV file into which all submissions will be saved (optional):

    handler1.csv_log = /var/log/handler1-log.csv

The Jinja2 template for the email. This is where the recipient email addresses
are entered.
[(See an example email template here.)](formmail/test/template/test.mail)

    handler1.template = formmail/handler1/mail-template.tmpl

The `handler1.fields.xxx` subgroup includes the descriptions of the form
fields, and these must match the fields on the form. These are the fields
expected in the POST request and then made available to the template. Each
variable in the group defines a field and its value can be:
* "mandatory" (which makes the field mandatory)
* and/or "email" (which makes the field an email)
* or it can be empty (just a normal optional field).

For mandatory fields we can also set "group-name.fields.field-name.mandatory"
to override the error message that will be returned by the handler if the field
was empty. Likewise for email fields we can define
"group-name.fields.field-name.email" to set the error message that's returned
if the content of the field doesn't look like an email. See an example:

    handler1.fields.email = mandatory, email
    handler1.fields.email.mandatory = You failed the email test
    handler1.fields.email.email = You failed the email validation
    handler1.fields.non_mandatory_email = email
    handler1.fields.non_mandatory_message =
    handler1.fields.mandatory = mandatory
