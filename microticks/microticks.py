"""
TODO:
    http://flask.pocoo.org/docs/0.12/tutorial/packaging/#tutorial-packaging


"""
import sqlite3
import sys
import os
import uuid
from datetime import datetime
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler

import yaml
from flask import Flask, g, request, redirect, url_for
from flask_json import FlaskJSON, JsonError, json_response, as_json
from flask_cors import CORS, cross_origin
from raven.contrib.flask import Sentry


class Database(object):

    def __init__(self, filename):
        self.filename = filename
        self.events = Events(self)
        self.sessions = Sessions(self)
        self.open()

    def init(self):
        self.events.init()
        self.sessions.init()

    def open(self):
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row

    def update(self, query, *args):
        c = self.conn.execute(query, *args)
        self.conn.commit()
        return c

    def select(self, query, *args):
        return self.conn.execute(query, *args)

    def close(self):
        return self.conn.close()

    def cleanup(self):
        """
        Cleanup the database upon start
        """
        self.sessions.cleanup()  # First delete any dangling sessions
        self.events.cleanup()    # Then delete any dangling events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Sessions(object):

    def __init__(self, db):
        self.db = db

    def init(self):
        """
        Create the database table
        """
        n = self.db.update('''
            CREATE TABLE IF NOT EXISTS `sessions` (
              `id`  INTEGER PRIMARY KEY AUTOINCREMENT,
              `token`  TEXT NOT NULL,
              `ip`  TEXT NOT NULL,
              `started_at`  TEXT NOT NULL,
              `stopped_at`  TEXT
            );
        ''')
        app.logger.info('Table created: sessions')

    def stop(self, token):
        """
        Stop a session.

        Args:
            token (string): The session token

        Returns:
            True if successful or False if the session was not found.
        """
        session = self.get(token)

        c = self.db.update('UPDATE `sessions` SET stopped_at=? WHERE id=?',
                           (datetime.now().strftime('%F %T'), session['id'],))

    def start(self):
        """
        Start a new session and return the session token
        """
        token = uuid.uuid4().hex
        c = self.db.update('INSERT INTO `sessions` (started_at, token, ip) VALUES (?, ?, ?)',
                           (datetime.now().strftime('%F %T'), token, request.remote_addr))
        if c.rowcount == 0:
            raise JsonError(description='Could not store new session in DB')
        return token

    def get(self, token):
        sessions = list(self.db.select('SELECT * FROM `sessions` WHERE token=?', (token,)))
        if len(sessions) == 0:
            raise JsonError(description='Could not find session')

        if sessions[0]['stopped_at'] is not None:
            raise JsonError(description='Session was already stopped.')

        return sessions[0]

    def cleanup(self):
        """
        Delete any dangling session
        """
        c = self.db.update('DELETE FROM `sessions` WHERE `stopped_at` IS NULL')
        app.logger.info('Cleaned up %s sessions' % (c.rowcount,))


class Events(object):

    def __init__(self, db):
        self.db = db

    def init(self):
        """
        Create the database table
        """
        self.db.update('''
            CREATE TABLE IF NOT EXISTS `events` (
              `id`  INTEGER PRIMARY KEY AUTOINCREMENT,
              `session_id` INTEGER NOT NULL,
              `time`  TEXT NOT NULL,
              `action` TEXT NOT NULL,
              `category` TEXT,
              `extras` TEXT
            );
        ''')
        app.logger.info('Table created: events')

    def store(self, session, action, category, extras):
        """
        Store a new event and return the event id

        Args:
            session (sqlite3.Row)
            action (string)
            category (string)
            extras (string)

        Returns:
            The ID of the created event
        """

        c = self.db.update('INSERT INTO `events` (session_id, time, action, category, extras) VALUES (?, ?, ?, ?, ?)',
                           (session['id'], datetime.now().strftime('%F %T'), action, category, extras))

        return c.lastrowid

    def get(self):
        events = []
        for row in self.db.select('SELECT * FROM `events`'):
            events.append(row)

        return events

    def cleanup(self):
        """
        Delete any dangling events
        """
        c = self.db.update('DELETE FROM events WHERE id IN (SELECT events.id FROM events LEFT JOIN sessions ON events.session_id=sessions.id WHERE sessions.id IS NULL)')
        app.logger.info('Cleaned up %s events' % (c.rowcount,))


# -----------------------------------------------------------------------------
# Make ze app

def create_app():
    app = Flask(__name__)
    FlaskJSON(app)
    CORS(app)

    # Load config from environment
    for key in ['MICROTICKS_SENTRY_DSN']:
        if os.environ.get(key):
            app.config.update({key: os.environ.get(key)})

    if app.config.get('MICROTICKS_SENTRY_DSN') is not None:
        # Optional: Use Sentry to log errors if configured in the config file
        sentry = Sentry(app, dsn=app.config['SENTRY_DSN'])

    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    return app


app = create_app()

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
    app.logger.setLevel(logging.INFO)
    app.logger.info('Instance path: %s', app.instance_path)
    get_db().cleanup()
    app.logger.info('DB cleanup done')

# -----------------------------------------------------------------------------
# API key middleware

def api_key_required(f):
    # http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.args.get('key') is None:
            raise JsonError(description='Please specify an API key using the "key" query string parameter.', status=401)
        if request.args.get('key') != config['api_key']:
            raise JsonError(description='The key is not valid.', status=401)
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
def start_session():
    token = get_db().sessions.start()
    return json_response(token=token)


@app.route('/sessions/stop', methods=['POST'])
def stop_session():
    token = request.form.get('token')
    status = get_db().sessions.stop(token)

    return json_response()


@app.route('/events', methods=['POST'])
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

