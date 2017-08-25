"""
TODO (maybe): http://flask.pocoo.org/docs/0.12/tutorial/packaging/#tutorial-packaging
"""
import sys
import os
from functools import wraps
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import yaml
import click
from flask import Flask, g, request, redirect, url_for, render_template
from flask_json import FlaskJSON, JsonError, json_response, as_json
from flask_cors import CORS, cross_origin
from flask_log import Logging
from raven.contrib.flask import Sentry

from .database import Database


app = Flask(__name__)


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

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


@app.cli.command('createconsumer')
@click.option('--ip_filter', help='IP filter')
@click.argument('name')
def createconsumer_command(name, ip_filter):
    """Create a new consumer key."""
    key = get_db().consumers.create(name)
    print('Created new consumer "%s"' % (name,))
    print('Consumer key: %s' % (key,))


def validate_consumer_key():
    return get_db().consumers.validate(request.form.get('consumer_key'))


@app.before_first_request
def startup():

    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(module)s:%(funcName)s\t%(message)s')
    handler = RotatingFileHandler(os.path.join(app.instance_path, 'microticks.log'), maxBytes=100000, backupCount=3)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    app.logger.info('Instance path: %s', app.instance_path)
    # get_db().cleanup()
    # app.logger.info('DB cleanup done')


def require_fields(fields):
    for fieldname in fields:
        if request.form.get(fieldname) is None:
            raise JsonError(error='No "%s" parameter provided' % (fieldname,), status=400)

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
@api_key_required
def hello():
    now = datetime.now()
    return render_template('index.html', today=now.strftime('%F'))


@app.route("/dash")
@api_key_required
def dash():
    now = datetime.now()
    return render_template('dash.html', today=now.strftime('%F'))


@app.route('/sessions', methods=['POST'])
def start_session():
    consumer_id = validate_consumer_key()
    require_fields(['ts'])
    token = get_db().sessions.start(request.remote_addr, request.form.get('ts'), consumer_id)
    return json_response(token=token)


@app.route('/sessions/stop', methods=['POST'])
def stop_session():
    require_fields(['ts', 'token'])
    status = get_db().sessions.stop(request.form.get('token'), request.form.get('ts'))

    return json_response()


@app.route('/sessions', methods=['GET'])
def get_sessions():
    # validate_consumer_key()
    sessions = get_db().sessions.find(request.args)
    return json_response(sessions=sessions, count=len(sessions))


@app.route('/events', methods=['POST'])
def store_event():
    require_fields(['token', 'action', 'data', 'ts'])
    db = get_db()
    event_id = db.events.store(db.sessions.get(request.form.get('token')),
                               request.form.get('action'),
                               request.form.get('data'),
                               request.form.get('ts'))
    return json_response(event_id=event_id)

@app.route('/events', methods=['GET'])
def get_events():
    # validate_consumer_key()
    events = get_db().events.find(request.args)
    return json_response(events=events, count=len(events))

