#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Migrate the users table of the server database: primary key (name) -> (name, token)

A user is identified by name + token: the same name (e.g. an email) can have several
accounts, one per token. In databases created by previous versions, the primary key of
the users table is the name only: then a request with an existing name and another token
fails (instead of creating another account).

    python -m uws_server.migrate_users            # dry run: show the current schema
    python -m uws_server.migrate_users --apply    # migrate the users table

Backup the database before --apply. The migration is done in a transaction, and does
nothing if the table is already migrated.
"""

import argparse

from sqlalchemy import inspect, text

from . import storage
from .settings import logger, settings

NEW_PK = ["name", "token"]


def users_pk(engine):
    return inspect(engine).get_pk_constraint("users")["constrained_columns"]


def check_users_schema(job_storage=None):
    """Log a warning if the users table has the primary key of previous versions"""
    job_storage = job_storage or getattr(storage, settings.STORAGE + "JobStorage")()
    pk = users_pk(job_storage.engine)
    if pk != NEW_PK:
        logger.warning(
            f"users table primary key is {pk}, run: python -m uws_server.migrate_users --apply"
        )
    return pk


def migrate(apply=False):
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    engine = job_storage.engine
    pk = users_pk(engine)
    print(f"users table ({engine.dialect.name}): primary key {pk}")
    if pk == NEW_PK:
        print("Already migrated, nothing to do")
        return
    with engine.connect() as conn:
        n_users = conn.execute(text("SELECT count(*) FROM users")).scalar()
        empty = conn.execute(text("SELECT name FROM users WHERE token IS NULL OR token = ''")).scalars().all()
    print(f"{n_users} users, {len(empty)} without token (a random token will be set)")
    if not apply:
        print("Dry run, nothing changed (use --apply to migrate)")
        return
    columns = [c.name for c in job_storage.User.__table__.columns]
    with engine.begin() as conn:
        for name in empty:
            conn.execute(
                text("UPDATE users SET token = :token WHERE name = :name AND (token IS NULL OR token = '')"),
                {"token": settings.new_token(), "name": name},
            )
        if engine.dialect.name == "sqlite":
            # SQLite cannot change a primary key: rebuild the table
            conn.execute(text("ALTER TABLE users RENAME TO users_old"))
            job_storage.User.__table__.create(conn)
            cols = ", ".join(columns)
            conn.execute(text(f"INSERT INTO users ({cols}) SELECT {cols} FROM users_old"))
            conn.execute(text("DROP TABLE users_old"))
        else:
            pk_name = inspect(conn).get_pk_constraint("users")["name"]
            conn.execute(text(f'ALTER TABLE users DROP CONSTRAINT "{pk_name}"'))
            conn.execute(text("ALTER TABLE users ALTER COLUMN token SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD PRIMARY KEY (name, token)"))
    print(f"Migrated: primary key {users_pk(engine)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="migrate the users table")
    args = parser.parse_args()
    migrate(apply=args.apply)
