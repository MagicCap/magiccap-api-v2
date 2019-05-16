# This code is a part of MagicCap which is a MPL-2.0 licensed project.
# Copyright (C) Jake Gealer <jake@gealer.email> 2019.

from sanic import Blueprint, response
from hashlib import sha512
from uuid import uuid4
import aiohttp
import rethinkdb as r
# Imports go here.

install_id = Blueprint("install_id", url_prefix="/install_id")
# The install ID blueprint.


async def get_device_id(app, device_id):
    """Gets the device ID."""
    arr = await r.table("installs").get_all(device_id, index="device_id").coerce_to("array").run(app.conn)
    if len(arr) == 0:
        return

    return arr[0]


@install_id.route("/new/<device_id>")
async def new_install_id(request, device_id):
    """Creates a new install ID."""
    install_id_db = await get_device_id(request.app, device_id)
    if not install_id_db:
        ip = request.remote_addr
        install_id_db = {
            "id": str(uuid4()),
            "device_id": device_id,
            "ip_last_5": sha512(ip.encode()).hexdigest()[-5:]
        }
        await r.table("installs").insert(install_id_db).run(request.app.conn)

    return response.text(install_id_db['id'])


@install_id.route("/validate/<i_id>")
async def validate_install_id(request, i_id):
    """Validates a install ID."""
    install_id_db = await r.table("installs").get(i_id).run(request.app.conn)
    if not install_id_db:
        return response.json({
            "exists": False
        }, status=404)

    return response.json({
        "exists": True,
        "ip_hash_last_5": install_id_db['ip_last_5']
    })


def setup(app):
    app.register_blueprint(install_id, url_prefix="/install_id")
# Sets up the API.
