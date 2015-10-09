# sitescripts.testpages

## Introduction

This package contains all the dynamic URL handlers required for the otherwise
static testpages.adblockplus.org project. This allows us to create test cases
for things like sitekeys which require web responses to be generated
dynamically.


## sitescripts.testpages.web.sitekey_frame

For test cases that test the $sitekey filter option you can use the make use of
the `/sitekey-frame` URL handler. The handler renders a template of your
choosing, passing in the public key and signature variables. For this you will
need to have a suitable RSA key file, a Jinja2 template that makes use of the
`public_key` + `signature` variables and a suitable `sitescripts.ini`
configuration.

Here's an example configuration:

```
[multiplexer]
sitescripts.testpages.web.sitekey_frame =

[testpages]
sitekeyFrameTemplate=%(root)s/testpages.adblockplus.org/templates/sitekey_frame.tmpl
sitekeyPath=%(root)s/testpages.adblockplus.org/static/site.key
```

The handler automatically sets the correct `X-Adblock-Key` response header but
it's important that the template also populates the `data-adblockkey` attribute
of the html element with the public key and signature. For example:

    <html data-adblockkey="{{ public_key + "_" + signature }}">
