# Microticks

Microservice for collecting simple analytics data (sessions and session events)
in a SQLite database.

### Usage

```
POST /sessions
    Start a new session and get a session token.

POST /sessions/stop
    Stop a session.

POST /events
    Store a new event.
```

### Setup

```
$ virtualenv --no-site-packages ENV
$ . ENV/bin/activate
$ pip install --editable .
```

### Run dev server

Define the environment variables, initialize the database, then create a
consumer key for your frontend app:

```
$ export FLASK_APP=microticks
$ export FLASK_DEBUG=true
$ flask initdb
$ flask createconsumer MyApp
$ flask run
```

### Production

Optional config:

```
export FLASK_LOG_LEVEL=INFO

# Log errors to Sentry
export MICROTICKS_SENTRY_DSN=...

# Require an api key for every request
export MICROTICKS_KEY=my-secret-key
```

```
gunicorn --workers 2 --bind 127.0.0.1:8001 wsgi
```

### Apache config

Note: [The Alias directive takes precedence over WSGIScriptAlias](https://serverfault.com/questions/59791/configure-apache-to-handle-a-sub-path-using-wsgi/59920#59920), so you cannot
mount WSGI application under a URL specified by Alias directive.

```
<VirtualHost *:80>
    DocumentRoot "/data/www/"

    WSGIDaemonProcess microticks python-home=/data/microticks/api/ENV

    Alias /microticks/api /data/microticks/api/wsgi.py
    Alias /microticks /data/microticks/static
    <Directory /data/microticks/api>
        WSGIProcessGroup microticks
        WSGIApplicationGroup %{GLOBAL}
        AddHandler wsgi-script .py
        Options ExecCGI
        Require all granted
    </Directory>

    <Directory /data/microticks/static>
        AllowOverride None
        # Options Indexes FollowSymLinks
        # Allow open access:
        Require all granted
    </Directory>
</VirtualHost>
```
