# oauth2dl 

This is a script that downloads a file from a given URL 
using Google Oauth2 for service accounts.

## Dependencies

* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [oauth2client](https://github.com/google/oauth2client) Using pip:
```commandline
    pip install oauth2client
```
* [httplib2](https://github.com/httplib2/httplib2) Using pip:
```commandline
    pip install httplib2
```
    
## Running the script

The script can be run as a module, using the following command:

```commandline
    python -m sitescripts.oauth2dl.bin.oauth2dl [-k <key-file>] [-s <scope>] [-o <path>] <url>
```

where: 
* `key-file` = Path to the key file used to authenticate. If not provided, uses
the `OAUTH2DL_KEY` environment variable.
* `scope` = The scope used when authenticating(eg:
https://www.googleapis.com/auth/drive). If not provided, uses the `OAUTH2DL_SCOPE`
environment variable.

* `path` = Path where to save the downloaded file. If not provided, the 
contents will be sent to `stdout`
* `url` = URL of the file we're trying to download. For a Google Drive 
file, the url should look something like:  
`https://www.googleapis.com/drive/v3/files/<fileID>?alt=media`

The script can also be run directly from the file, using:
```commandline
    python sitescripts/oauth2dl/bin/oauth2dl.py [-k <key-file>] [-s <scope>] [-o <path>] <url>
```

## Getting the key file

The key file can be obtained by following the instructions available 
[here](https://developers.google.com/identity/protocols/OAuth2ServiceAccount).

It should be a JSON with the following format: 
```json
    {
      "type": "service_account",
      "project_id": <project_id>,
      "private_key_id": <private_key_id>,
      "private_key": <RSA-encrypted private key>,
      "client_email": "<service_account_id>@<project_id>.iam.gserviceaccount.com",
      "client_id": <client_id>,
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://accounts.google.com/o/oauth2/token",
      "auth_provider_x509_cert_url": ...,
      "client_x509_cert_url": ...
}
```

In order to download the file the *service account* (i.e. the email in 
the `client_id` field from the key file) should be granted access to it.


