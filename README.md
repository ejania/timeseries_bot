# TimeSeries bot
To install dependencies using pip, run:
```sh
pip install cherrypy requests pyTelegramBotAPI
```

You'll need a bunch of files that are not commited to the repository. All of them should be placed in root directory of the project:
- file containing your api token, `api_token.txt `
- files with your private and public SSL keys, `webhook_pkey.pem` and `webhook_cert.pem`

To generate your own self-signed SSL keys, use 
```sh
openssl genrsa -out webhook_pkey.pem 2048
openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
```
When asked for "Common Name (e.g. server FQDN or YOUR name)" you should put your hostname or your public IP address if you don't have one.