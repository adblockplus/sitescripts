# Sitescripts

## Introduction

The sitescripts repository contains many of the server side Python scripts that
we use. There are both web handlers, which can be used via the multiplexer, and
scripts that perform other tasks.

The scripts are often unrelated and as such will not all be documented here. For
more information about the individual scripts you will need to look at their
included README files. (For undocumented scripts you will need to either look at
the code itself, or refer to the issue numbers as mentioned in the related
commits.)


## sitescripts.ini

Many of the scripts included in this repository need some configuration in order
to work. For this there is a shared configuration file called `sitescripts.ini`.
The file contains different sections for the different scripts and some shared
configuration.

The following paths will be checked - in order - for the scriptscripts
configuration file:

1. ~/.sitescripts
2. ~/sitescripts.ini
3. /etc/sitescripts
4. /etc/sitescripts.ini

There is also an environment variable `SITESCRIPTS_CONFIG` that can be used to
provide a custom path for the configuration file. This custom path will be
checked first, effectively at position 0 of the list above.

The first configuration file that is found will be used exclusively. So for
example if you have both a ~/.sitescripts file and a ~/sitescripts.ini file the
latter will be ignored, and if you specify a valid custom path with
`SITESCRIPTS_CONFIG` all the other files will be ignored.

The `DEFAULT` section contains some of the more generic configuration options
that are shared by the various scripts.

The `multiplexer` section is used to configure which URL handlers are included
by the multiplexing web server. Each option key specifies a module to import,
the values are not used and should be left blank.

We won't go into the other sections of the configuration file here, but for an
example that includes them all take a look at `.sitescripts.example`.


## Multiplexer

Many of the scripts in this repository contain URL handlers which are used when
we need to dynamically handle web requests to our servers. For example, we might
need to automatically send an email after a web request has been received.

These URL handlers are functions that conform to [the WSGI standard as specified
in PEP-333](https://www.python.org/dev/peps/pep-0333/). They will almost always
use some of the decorators and utilities that are provided by `sitescripts.web`,
for example the `url_handler` decorator which registers a handling function with
the multiplexer for the given path.

The multiplexer imports each module that's listed in the `multiplexer` section
of the sitescripts configuration file, before providing a WSGI app that serves
any URL handlers that they have registered.

This WSGI app can then be served using `multiplexer.fcgi` in production, or
`multiplexer.py` in development. `multiplexer.fcgi` is a FCGI script and depends
on [the flup package](http://www.saddi.com/software/flup/).
`multiplexer.py` provides a complete web server and only optionally depends on
[the werkzeug package](http://werkzeug.pocoo.org/). (If werkzeug is available
its debugging facilities will be used.)

So, to test any of the URL handlers in development do the following:

1. Create a sitescripts configuration file that lists the web modules that you
are testing under the `multiplexer` section. (Depending on the modules you are
testing you may need to add additional configuration as well.)
2. Save the configuration file somewhere where it will be found, for example
`~/.sitescripts`.
3. Type `python multiplexer.py`, it will start a web server at
http://localhost:5000/ . This web server will use any URL handlers that have
been defined in the modules you are testing to respond to requests.


## Testing

There are tests for some parts of the functionality of sitescripts. They are
located in `test` directories and can be run via
[Tox](https://tox.readthedocs.org/): 

    $ tox
