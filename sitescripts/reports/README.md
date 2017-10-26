# Scripts and web handlers for reports

## resolveReport

This handler is mounted under `/resolveReport` and should be called as follows:

    http://<hostname>/<prefix>/resolveReport?<encrypted-report-id>

If the report id is successfully decrypted, a `302 Found` response will be
returned redirectring to the url of the report. If the encrypted report id
is in the wrong format or encryption fails, a `404 Not Found` response will be
returned.

### Configuration

The handler is configured via sitescripts config. In order to activate this
handler, add the following line to multiplexer config:

    [multiplexer]
    sitescripts.reports.web.resolveReport =

Its own configuration is in the section `reports_anonymization`:

    [reports_anonymization]
    encryption_key = <base64-encrypted-key>
    redirect_url = https://target.host.com/reports/{report_id}

The redirect URL could be any string. `{report_id}` will be replaced by
the decrypted id of the report.
