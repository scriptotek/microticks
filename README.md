# Microticks

Microservice for collecting analytics data in a SQLite database.

### Setup

```
$ virtualenv --no-site-packages ENV
$ . ENV/bin/activate
$ pip install --editable .
```

### Run dev server

```
$ export FLASK_APP=microticks
$ export FLASK_DEBUG=true
$ flask initdb
$ flask run
```

### Production

Setup Apache to use `microticks.wsgi`.

See http://flask.pocoo.org/docs/0.12/deploying/mod_wsgi/
