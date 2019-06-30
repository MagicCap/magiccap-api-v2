import rethinkdb as r


class VersionCache:
    """
    Apparently RethinkDB is not capable of handling indexes without hitting 100 reads/second and shitting itself.
    It's fine though. This is probably a bit quicker.
    """
    def __init__(self, conn, loop):
        self.loop = loop
        self.conn = conn
        self.loop.create_task(self._handle_db())
        self._cache = []

    async def _handle_db(self):
        self._cache = await r.table("versions").order_by(index="release_id").coerce_to("array").run(self.conn)
        feed = await r.table("versions").changes().run(self.conn)
        while await feed.fetch_next():
            change = await feed.next()
            old = change['old_val']
            new = change['new_val']     
            if old:
                if new:
                    for i in self._cache:
                        if i['id'] == old['id']:
                            for k in new.keys():
                                i[k] = new[k]
                else:
                    for i in self._cache:
                        if i['id'] == old['id']:
                            self._cache.remove(i)
            else:
                self._cache.append(new)

    def since_version_id(self, version_id):
        i = 0
        x = []
        for version in self._cache:
            if i >= version_id:
                x.append(version)
            else:
                i += 1
        return x

    def get_latest(self):
        indexed_length = len(self._cache) - 1
        beta_res = None
        release_res = None

        while True:
            if beta_res and release_res:
                break

            item = self._cache[indexed_length]
            if item['beta']:
                beta_res = item
            else:
                release_res = item
            indexed_length -= 1

        return (beta_res, release_res)
