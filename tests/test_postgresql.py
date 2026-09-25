#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Test of the migration of a server database of a previous version on PostgreSQL (uws_server.migrate_users,
uws_client.rotate_tokens), with a temporary PostgreSQL container (same image as docker-compose.dist.yml)

Skipped if Docker is not available.
"""

import shutil
import socket
import subprocess
import time
import uuid

import pytest
from sqlalchemy import text

from uws_client import rotate_tokens
from uws_client import uws_client as c
from uws_server import migrate_users, storage

IMAGE = "postgres:18"
PASSWORD = "opus-test"
# predictable token of a previous version (replaced by rotate_tokens)
ALICE_TOKEN = rotate_tokens.legacy_token("alice", rotate_tokens.APP_PATH)


def docker_available():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not docker_available(), reason="Docker is not available")


@pytest.fixture(scope="module")
def postgresql():
    """Temporary PostgreSQL container, removed after the tests, yields the database URL"""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    name = f"opus-test-pg-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:5432",
         "-e", "POSTGRES_USER=opus", "-e", f"POSTGRES_PASSWORD={PASSWORD}", "-e", "POSTGRES_DB=opus", IMAGE],
        check=True, capture_output=True, timeout=300,
    )
    try:
        for _ in range(60):
            ready = subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "opus", "-d", "opus"],
                                   capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            pytest.fail("PostgreSQL container not ready")
        yield f"postgresql://opus:{PASSWORD}@127.0.0.1:{port}/opus"
    finally:
        subprocess.run(["docker", "stop", name], capture_output=True)


@pytest.fixture
def old_db(postgresql, monkeypatch):
    """Server database with the users and entities tables of previous versions"""
    real_storage = storage.SQLAlchemyJobStorage
    monkeypatch.setattr(storage, "SQLAlchemyJobStorage", lambda: real_storage(db_string=postgresql))
    engine = storage.SQLAlchemyJobStorage().engine  # create the tables (current schema)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE entities DROP COLUMN owner_token"))
        pk = conn.execute(text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_name = 'users' AND constraint_type = 'PRIMARY KEY'"
        )).scalar()
        conn.execute(text(f'ALTER TABLE users DROP CONSTRAINT "{pk}"'))
        conn.execute(text("ALTER TABLE users ALTER COLUMN token DROP NOT NULL"))
        conn.execute(text("ALTER TABLE users ADD PRIMARY KEY (name)"))
        conn.execute(text(f"""
            INSERT INTO users (name, token, roles) VALUES ('alice', '{ALICE_TOKEN}', 'job1'), ('bob', NULL, '');
            INSERT INTO jobs (jobid, jobname, owner, owner_token, phase) VALUES
                ('j1', 'job1', 'alice', '{ALICE_TOKEN}', 'COMPLETED'),
                ('j2', 'job1', 'alice', 'alice-token2', 'COMPLETED'),
                ('j3', 'job1', 'mallory', 'mallory-token', 'COMPLETED');
            INSERT INTO entities (entity_id, jobid, owner) VALUES
                ('generated', 'j1', 'alice'),  -- result of job j1
                ('uploaded', NULL, 'alice'),  -- file uploaded for job j2
                ('orphan', NULL, 'alice'),  -- no known job
                ('mismatch', 'j3', 'alice');  -- job of another owner: token not taken
            INSERT INTO used (entity_id, jobid, owner) VALUES ('uploaded', 'j2', 'alice');
        """))
    return engine


def rows(engine, query):
    with engine.connect() as conn:
        return conn.execute(text(query)).all()


def test_migration(old_db, capsys):
    engine = old_db
    assert migrate_users.users_pk(engine) == ["name"]
    assert not migrate_users.entities_owner_token(engine)
    # dry run
    migrate_users.migrate()
    out = capsys.readouterr().out
    assert "owner_token column missing" in out and "1 without token" in out
    assert migrate_users.users_pk(engine) == ["name"]
    assert not migrate_users.entities_owner_token(engine)
    # entities (done at the start of the server)
    assert migrate_users.migrate_entities()
    assert dict(rows(engine, "SELECT entity_id, owner_token FROM entities")) == {
        "generated": ALICE_TOKEN, "uploaded": "alice-token2", "orphan": None, "mismatch": None,
    }
    assert not migrate_users.migrate_entities()  # nothing to do the second time
    # users
    migrate_users.migrate(apply=True)
    assert migrate_users.users_pk(engine) == ["name", "token"]
    users = rows(engine, "SELECT name, token, roles FROM users ORDER BY name")
    assert users[0] == ("alice", ALICE_TOKEN, "job1")
    assert users[1][0] == "bob" and users[1][1]  # a random token was set
    job_storage = storage.SQLAlchemyJobStorage()
    job_storage.add_user("alice", token="other-token")  # same name, other token: another account
    assert len(job_storage.get_users(name="alice")) == 2
    capsys.readouterr()
    migrate_users.migrate(apply=True)
    assert "Already migrated" in capsys.readouterr().out
    # replacement of the tokens: client, server account, jobs and their files
    email = "alice"
    with c.app.app_context():
        c.user_datastore.create_user(email=email, token=ALICE_TOKEN, roles=["user"])
        c.db.session.commit()
    try:
        rotate_tokens.rotate(apply=True)
        with c.app.app_context():
            new = c.User.query.filter_by(email=email).one().token
        assert new != ALICE_TOKEN
        assert dict(rows(engine, "SELECT jobid, owner_token FROM jobs"))["j1"] == new
        entities = dict(rows(engine, "SELECT entity_id, owner_token FROM entities"))
        assert entities["generated"] == new
        assert entities["uploaded"] == "alice-token2"  # other account, not replaced
    finally:
        with c.app.app_context():
            c.user_datastore.delete_user(c.User.query.filter_by(email=email).one())
            c.db.session.commit()
