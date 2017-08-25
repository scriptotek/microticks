# Microticks

Microservice for collecting simple analytics data (sessions and session events)
in a SQLite database.

Starting (and optionally, stopping) sessions is up to the frontend. Microticks was
developed for use with a touch table ("digital signage") app where users cannot
navigate to and from the app, so the frontend starts a session upon the first
touch event and stops it when no events have been registered for some time – when
we assume that the user has walked away. An alternative could be to use some kind
of proximity sensor. When to start and optionally stop sessions is completely up
to the frontend.

### Usage

For a simple example frontend that tracks clicks and sends them to the Microticks
server, see the "examples" folder.

* `POST /sessions`: Start a new session and get a session token. Arguments:

    - `consumer_key`: A key that identifies the app.
      Created by running `flask createconsumer NAME`, see below.
    - `ts`: timestamp. Example: '2017-08-25T17:09:19.438Z'

* `POST /sessions/stop`: Stop a session.

* `POST /events`:  Store a new event. Arguments:

    - `action`: Some event action or category. Example: `'click'`
    - `data`: Event data. Example: `'{"target":"some_element", "clickX":406, "clickY":300}'`
    - `token`: session token
    - `ts`: timestamp. Example: `'2017-08-25T17:09:19.438Z'`

### Setup

```
$ virtualenv --no-site-packages ENV
$ . ENV/bin/activate
$ pip install --editable .
```

### Run dev server

Define the environment variables, initialize the database, then create a
consumer key for your frontend app and start the server that listens for
analytics events from your frontend.

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
