from datetime import datetime
import uuid
import logging

from flask_json import JsonError

class Sessions(object):

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)

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
              `stopped_at`  TEXT,
              `consumer_id`  INTEGER NOT NULL
            );
        ''')
        self.logger.info('Table created: sessions')

    def stop(self, token, timestamp):
        """
        Stop a session.

        Args:
            token (string): The session token

        Returns:
            True if successful or False if the session was not found.
        """
        session = self.get(token)

        c = self.db.update('UPDATE `sessions` SET stopped_at=? WHERE id=?',
                           (timestamp, session['id'],))

    def start(self, ip, timestamp, consumer_id):
        """
        Start a new session and return the session token
        """
        token = uuid.uuid4().hex
        c = self.db.update('INSERT INTO `sessions` (started_at, token, ip, consumer_id) VALUES (?, ?, ?, ?)',
                           (timestamp, token, ip, consumer_id))
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
        Delete dangling sessions
        """
        c = self.db.update('DELETE FROM `sessions` WHERE `stopped_at` IS NULL')
        self.logger.info('Cleaned up %s sessions' % (c.rowcount,))
