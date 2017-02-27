from datetime import datetime
import uuid
import logging

from flask_json import JsonError

class Consumers(object):

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def init(self):
        """
        Create the database table
        """
        n = self.db.update('''
            CREATE TABLE IF NOT EXISTS `consumers` (
              `id`  INTEGER PRIMARY KEY AUTOINCREMENT,
              `name` TEXT NOT NULL UNIQUE,
              `key`  TEXT NOT NULL,
              `ip_filter`  TEXT,
              `created_at`  TEXT NOT NULL,
              `deleted_at`  TEXT
            );
        ''')
        self.logger.info('Table created: consumers')

    def create(self, name, ip_filter=None):
        """
        Create a new consumer key
        """
        key = uuid.uuid4().hex
        c = self.db.update('INSERT INTO `consumers` (name, key, created_at, ip_filter) VALUES (?, ?, ?, ?)',
                           (name, key, datetime.now().strftime('%F %T'), ip_filter))
        if c.rowcount == 0:
            raise JsonError(description='Could not store new consumer in DB')
        return key

    def validate(self, key):
        consumers = list(self.db.select('SELECT id, deleted_at FROM `consumers` WHERE key=?', (key,)))
        if len(consumers) == 0:
            raise JsonError(error='Invalid consumer_key')

        if consumers[0]['deleted_at'] is not None:
            raise JsonError(error='Consumer is not active.')

        return consumers[0]['id']
