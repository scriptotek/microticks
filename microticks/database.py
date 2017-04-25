import sqlite3

from .consumers import Consumers
from .events import Events
from .sessions import Sessions

class Database(object):

    def __init__(self, filename):
        self.filename = filename
        self.consumers = Consumers(self)
        self.events = Events(self)
        self.sessions = Sessions(self)
        self.open()

    def init(self):
        self.consumers.init()
        self.events.init()
        self.sessions.init()

    def open(self):
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row

    def update(self, query, *args):
        c = self.conn.execute(query, *args)
        self.conn.commit()
        return c

    def select(self, query, args):
        return self.conn.execute(query, args)

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
