# This code is a part of MagicCap which is a MPL-2.0 licensed project.
# Copyright (C) Jake Gealer <jake@gealer.email> 2018-2019.

from sanic import response, Blueprint
import rethinkdb as r
# Imports go here.

version = Blueprint("version", url_prefix="/version")
# The version blueprint.


@version.route("/latest")
async def latest_versions(req):
    """Gets information about the latest MagicCap releases."""
    latest_release = None
    latest_beta = None

    versions = await r.table("versions").order_by(index="release_id").coerce_to("array").run(req.app.conn)
    for v in versions:
        if v['beta']:
            latest_beta = v
        else:
            latest_release = v

    beta_json = None
    beta_newer = False
    if latest_beta:
        beta_json = {
            "mac": "https://s3.magiccap.me/upgrades/v{}/magiccap-mac.dmg".format(latest_beta['id']),
            "linux": "https://s3.magiccap.me/upgrades/v{}/magiccap-linux.zip".format(latest_beta['id']),
            "changelogs": latest_beta['changelogs'],
            "version": latest_beta['id']
        }
        beta_newer = latest_beta['release_id'] > latest_release['release_id']

    return response.json({
        "beta": beta_json,
        "release": {
            "mac": "https://s3.magiccap.me/upgrades/v{}/magiccap-mac.dmg".format(latest_release['id']),
            "linux": "https://s3.magiccap.me/upgrades/v{}/magiccap-linux.zip".format(latest_release['id']),
            "changelogs": latest_release['changelogs'],
            "version": latest_release['id']
        },
        "is_beta_newer_than_release": beta_newer
    })


async def get_updates(version, app):
    """Gets all updates that is avaliable for the user."""
    updates = await r.table("versions").order_by(index="release_id").skip(
        version['release_id']).coerce_to("array").run(app.conn)

    return updates


@version.route("/check/<current_version>")
async def check_version(request, current_version):
    """An API used by MagicCap to check if it is the latest version."""
    beta_channel = request.args.get("beta", "false").lower() == "true"

    if current_version.startswith("v"):
        current_version = current_version.lstrip("v")
        if current_version == "":
            return response.json({
                "success": False,
                "error": "Version was solely v."
            }, status=400)

    version_db = await r.table("versions").get(current_version).run(request.app.conn)
    if not version_db:
        return response.json({
            "success": False,
            "error": "Version does not exist in the database."
        }, status=400)

    updates_since = await get_updates(version_db, request.app)
    changelogs = ""

    last_model = None

    for index, inbetween_release in enumerate(updates_since):
        if beta_channel == inbetween_release['beta']:
            last_model = inbetween_release
            if index + 1 != len(updates_since):
                changelogs += inbetween_release['changelogs'] + "\n"

    if not last_model:
        return response.json({
            "success": True,
            "updated": True
        })

    changelogs += last_model['changelogs'] + "\n"

    return response.json({
        "success": True,
        "updated": False,
        "latest": {
            "version": last_model['id'],
            "zip_paths": {
                "mac": "https://s3.magiccap.me/upgrades/v{}/magiccap-mac.zip".format(last_model['id']),
                "linux": "https://s3.magiccap.me/upgrades/v{}/magiccap-linux.zip".format(last_model['id'])
            }
        },
        "changelogs": changelogs
    })


def setup(app):
    app.blueprint(version, url_prefix="/version")
# Sets up the API.
