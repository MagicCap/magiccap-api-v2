from websockets import ConnectionClosed 
import ujson
import rethinkdb as r


class WebSocketManager:
    """Manages WebSockets on the web server."""
    def __init__(self, app, loop):
        self.app = app
        self.loop = loop
        self.app.add_websocket_route(self._handle_ws, "/version/feed")
        self.watchlist = {}
        loop.create_task(self._watch_versions())

    async def _watch_versions(self):
        feed = await r.table("versions").changes().run(self.app.conn)
        while await feed.fetch_next():
            change = await feed.next()
            old = change['old_val']
            new = change['new_val']
            if not old and new:
                del new['release_id']
                new['version'] = new['id']
                del new['id']

                serialized = ujson.dumps({"t": "update", "info": new})
                beta = new['beta']

                async def send_to_cat(cat):
                    for watcher in self.watchlist.get(cat, []):
                        try:
                            await watcher.send(serialized)
                        except ConnectionClosed:
                            self.watchlist[cat].remove(watcher)

                if beta:
                    await send_to_cat(True)
                else:
                    await send_to_cat(True)
                    await send_to_cat(False)

    async def _handle_ws(self, _, ws):
        watching = []
        while True:
            try:
                data = await ws.recv()
                try:
                    data = ujson.loads(data)
                except BaseException:
                    continue
                if isinstance(data, dict):
                    if data.get("t") == "watch":
                        if isinstance(data.get("beta", False), bool):
                            try:
                                self.watchlist[data.get("beta", False)].append(ws)
                            except KeyError:
                                self.watchlist[data.get("beta", False)] = [ws]
            except ConnectionClosed:
                break
