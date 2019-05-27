# This code is a part of MagicCap which is a MPL-2.0 licensed project.
# Copyright (C) Jake Gealer <jake@gealer.email> 2018-2019.

from sanic import Blueprint, response
import aiohttp
import rethinkdb as r
# Imports go here.

ci = Blueprint("ci", url_prefix="/ci")
# The ci blueprint.


@ci.route("/new/<ci_api_key>/<tag>")
async def new_version(request, ci_api_key, tag):
    """Allows CI to mark a new version during build."""
    if not await r.table("ci_keys").get(ci_api_key).run(request.app.conn):
        return response.text("API key is invalid.", status=403)

    if tag.startswith("v"):
        tag = tag.lstrip("v")

    i = await r.table("versions").count().run(request.app.conn)

    j = None
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.github.com/repos/JakeMakesStuff/MagicCap/releases/tags/v{}".format(tag)) as resp:
            resp.raise_for_status()
            j = await resp.json()

    await r.table("versions").insert({
        "release_id": i + 1,
        "id": tag,
        "changelogs": j['body'],
        "beta": "b" in tag
    }).run(request.app.conn)

    return response.text("Release {} successfully saved to the database.".format(tag))


def setup(app):
    app.blueprint(ci, url_prefix="/ci")
# Sets up the API.
