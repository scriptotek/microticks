from datetime import datetime
import logging
try:
    import ujson as json
except ImportError:
    import json
from .util import get_filters


class Events(object):

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)

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
              `data` TEXT
            );
        ''')
        self.logger.info('Table created: events')

    def store(self, session, action, data, timestamp):
        """
        Store a new event and return the event id

        Args:
            session (sqlite3.Row)
            action (string)
            data (string)
            timestamp (string)

        Returns:
            The ID of the created event
        """

        c = self.db.update('INSERT INTO `events` (session_id, time, action, data) VALUES (?, ?, ?, ?)',
                           (session['id'], timestamp, action, data))

        return c.lastrowid

    def find(self, args):
        events = []
        filters, filterargs, limit = get_filters(args)

        for row in self.db.select('''
            SELECT events.id, events.session_id, events.time, events.action, events.data FROM events
            LEFT JOIN sessions on sessions.id = events.session_id
            {} {}
            '''.format(filters, limit), filterargs):
            row = dict(zip(row.keys(), row))
            try:
                row['data'] = json.loads(row['data'])
            except ValueError:
                pass
            events.append(row)

        return events

    def cleanup(self):
        """
        Delete dangling events
        """
        c = self.db.update('DELETE FROM events WHERE id IN (SELECT events.id FROM events LEFT JOIN sessions ON events.session_id=sessions.id WHERE sessions.id IS NULL)')
        self.logger.info('Cleaned up %s events' % (c.rowcount,))

