# This code is a part of MagicCap which is a MPL-2.0 licensed project.
# Copyright (C) Jake Gealer <jake@gealer.email> 2019.

import sentry_sdk
from sentry_sdk.integrations.sanic import SanicIntegration
from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from pluginbase import PluginBase
from sanic_cors import CORS
from websocket_manager import WebSocketManager
from version_cache import VersionCache
import rethinkdb as r
import os
# Imports go here.


class RethinkSanic(Sanic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None
        r.set_loop_type("asyncio")
        self.register_listener(self._connect_rethinkdb, "before_server_start")
        self.search = None
        self.websocket_manager = None
        self.version_cache = None

    async def create_db_if_not_exists(self, db):
        try:
            await r.db_create(db).run(self.conn)
        except BaseException:
            pass

    async def create_table_if_not_exists(self, table):
        try:
            await r.table_create(table).run(self.conn)
        except BaseException:
            pass

    async def create_index_if_not_exists(self, table, *args, **kwargs):
        try:
            await r.table(table).index_create(*args, **kwargs).run(self.conn)
        except BaseException:
            pass

    @staticmethod
    async def _connect_rethinkdb(app, loop):
        app.conn = await r.connect(
            host=os.environ.get("RETHINKDB_HOSTNAME") or "127.0.0.1",
            user=os.environ.get("RETHINKDB_USER") or "admin",
            password=os.environ.get("RETHINKDB_PASSWORD") or ""
        )

        await app.create_db_if_not_exists("magiccap")
        app.conn.use("magiccap")

        await app.create_table_if_not_exists("versions")
        await app.create_table_if_not_exists("ci_keys")
        await app.create_table_if_not_exists("installs")

        await app.create_index_if_not_exists("versions", "release_id")
        await app.create_index_if_not_exists("versions", "beta")
        await app.create_index_if_not_exists("installs", "device_id")

        WebSocketManager(app, loop)
        app.version_cache = VersionCache(app.conn, loop)


app = RethinkSanic(__name__)
# Defines the app.

CORS(app)
# Allows CORS.

plugin_base = PluginBase(package="main.plugins")
plugin_source = plugin_base.make_plugin_source(
    searchpath=["./plugins"]
)
for plugin in plugin_source.list_plugins():
    loaded = plugin_source.load_plugin(plugin)
    loaded.setup(app)
# Loads all of the plugins.

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[SanicIntegration()]
)
# Loads in Sentry.

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0", protocol=WebSocketProtocol)
# Starts the app.
