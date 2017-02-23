"""
TODO (maybe): http://flask.pocoo.org/docs/0.12/tutorial/packaging/#tutorial-packaging
"""
import sys
import os
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler

import yaml
from flask import Flask, g, request, redirect, url_for
from flask_json import FlaskJSON, JsonError, json_response, as_json
from flask_cors import CORS, cross_origin
from flask_log import Logging
from raven.contrib.flask import Sentry

from .database import Database


app = Flask(__name__)

# Config defaults
app.config['FLASK_LOG_LEVEL'] = 'INFO'

# Load config from environment
for key in ['MICROTICKS_SENTRY_DSN', 'FLASK_LOG_LEVEL', 'MICROTICKS_KEY']:
    if os.environ.get(key):
        app.config.update({key: os.environ.get(key)})

if app.config.get('MICROTICKS_SENTRY_DSN') is not None:
    # Optional: Use Sentry to log errors if configured in the config file
    sentry = Sentry(app, dsn=app.config['MICROTICKS_SENTRY_DSN'])

# Middleware
FlaskJSON(app)
CORS(app)
Logging(app)

if not os.path.exists(app.instance_path):
    os.makedirs(app.instance_path)


def connect_db():
    """
    Instance path: See http://flask.pocoo.org/docs/0.12/config/#instance-folders
    """
    return Database(os.path.join(app.instance_path, 'microticks.db'))


def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    get_db().init()
    app.logger.info('Initialized the database.')


@app.before_first_request
def startup():

    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(module)s:%(funcName)s\t%(message)s')
    handler = RotatingFileHandler(os.path.join(app.instance_path, 'microticks.log'), maxBytes=100000, backupCount=3)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    app.logger.info('Instance path: %s', app.instance_path)
    get_db().cleanup()
    app.logger.info('DB cleanup done')

# -----------------------------------------------------------------------------
# API key middleware

def api_key_required(f):
    # http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config.get('MICROTICKS_KEY') is not None:
            if request.form.get('key') is None:
                raise JsonError(description='Please specify an API key using the "key" query string parameter.', status=401)
            elif request.form.get('key') != app.config.get('MICROTICKS_KEY'):
                raise JsonError(description='The key is not valid: .' + request.form.get('key'), status=401)
        return f(*args, **kwargs)
    return decorated_function


# -----------------------------------------------------------------------------
# App routes

@app.route("/")
def hello():
    return '''
    <pre>

    POST /sessions
        Start a new session and get a session token.

        Returns:
            {'status': 200, 'token': string}

    POST /sessions/stop
        Stop a session.

        Form data:
            token: string

        Returns:
            {'status': 200}

    POST /events

        Store a new event.

        Form data:
            token: the session token
            action: e.g. 'click_book',
            category: '???'
            extras: '???'

        Returns:
            {'status': 200, 'event_id': int}
    '''


@app.route('/sessions', methods=['POST'])
@api_key_required
def start_session():
    token = get_db().sessions.start(request.remote_addr)
    return json_response(token=token)


@app.route('/sessions/stop', methods=['POST'])
@api_key_required
def stop_session():
    token = request.form.get('token')
    status = get_db().sessions.stop(token)

    return json_response()


@app.route('/events', methods=['POST'])
@api_key_required
def store_event():
    token = request.form.get('token')
    action = request.form.get('action')
    category = request.form.get('category')
    extras = request.form.get('extras')
    db = get_db()
    event_id = db.events.store(db.sessions.get(token), action, category, extras)
    return json_response(event_id=event_id)

@app.route('/events', methods=['GET'])
def get_events():
    events = get_db().events.get()
    return json_response(events=events)

