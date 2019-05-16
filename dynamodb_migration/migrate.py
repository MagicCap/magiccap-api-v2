from models import *
import rethinkdb as r
import os
import json

conn = r.connect(
    host=os.environ.get("RETHINKDB_HOSTNAME") or "127.0.0.1",
    user=os.environ.get("RETHINKDB_USER") or "admin",
    password=os.environ.get("RETHINKDB_PASSWORD") or ""
)


def create_db_if_not_exists(db):
    try:
        r.db_create(db).run(conn)
    except BaseException:
        pass


def create_table_if_not_exists(table):
    try:
        r.table_create(table).run(conn)
    except BaseException:
        pass


def create_index_if_not_exists(table, *args, **kwargs):
    try:
        r.table(table).index_create(*args, **kwargs).run(conn)
    except BaseException:
        pass


print("Create DB/tables...")
create_db_if_not_exists("magiccap")
conn.use("magiccap")

create_table_if_not_exists("versions")
create_table_if_not_exists("ci_keys")
create_table_if_not_exists("installs")

create_index_if_not_exists("versions", "release_id")
create_index_if_not_exists("versions", "beta")
create_index_if_not_exists("installs", "device_id")


print("Migrating releases...")
for release in [Version._from_data(x) for x in json.loads(Version.dumps())]:
    r.table("versions").insert({
        "id": release.version,
        "release_id": release.release_id,
        "changelogs": release.changelogs,
        "beta": bool(release.beta)
    }).run(conn)


print("Migrating install ID's...")
for install in [InstallID._from_data(x) for x in json.loads(InstallID.dumps())]:
    r.table("installs").insert({
        "id": install.install_id,
        "device_id": install.device_id,
        "ip_last_5": install.hashed_ip[-5:]
    }).run(conn)


print("Migrating CI keys...")
for key in [TravisKeys._from_data(x) for x in json.loads(TravisKeys.dumps())]:
    r.table("ci_keys").insert({
        "id": key.key
    }).run(conn)
