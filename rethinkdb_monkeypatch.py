from rethinkdb import Connection


def auto_reconnect(self):
    if self._instance is None or not self._instance.is_open():
        self.reconnect()


Connection.check_open = auto_reconnect
