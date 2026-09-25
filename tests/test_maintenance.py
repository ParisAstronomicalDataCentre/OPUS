#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for the maintenance commands: migration of the users table of the server
(uws_server.migrate_users) and replacement of the predictable tokens (uws_client.rotate_tokens)
"""

import sqlite3
import time
import uuid

import pytest

from uws_client import rotate_tokens
from uws_client import uws_client as c
from uws_server import migrate_users, storage
from uws_server.settings import settings


class TestMigrateUsers:

    @pytest.fixture
    def old_db(self, tmp_path, monkeypatch):
        """Server database with the users table of previous versions (primary key: name)"""
        path = tmp_path / "old_job_database.db"
        real_storage = storage.SQLAlchemyJobStorage
        monkeypatch.setattr(storage, "SQLAlchemyJobStorage", lambda: real_storage(db_string=f"sqlite:///{path}"))
        storage.SQLAlchemyJobStorage().engine.dispose()  # create the tables
        db = sqlite3.connect(path)
        db.executescript("""
            ALTER TABLE users RENAME TO users_new;
            CREATE TABLE users (name VARCHAR(80) PRIMARY KEY, token VARCHAR(255), roles VARCHAR(255),
                                active VARCHAR(5), first_connection VARCHAR(19));
            DROP TABLE users_new;
            INSERT INTO users (name, token, roles) VALUES ('alice', 'alice-token', 'job1'), ('bob', NULL, '');
            INSERT INTO jobs (jobid, jobname, owner, owner_token, phase) VALUES ('j1', 'job1', 'alice', 'alice-token', 'COMPLETED');
        """)
        db.commit()
        db.close()
        return path

    def rows(self, path, query):
        with sqlite3.connect(path) as db:
            return db.execute(query).fetchall()

    def test_migration(self, old_db, capsys):
        job_storage = storage.SQLAlchemyJobStorage()
        assert migrate_users.check_users_schema(job_storage) == ["name"]
        # dry run
        migrate_users.migrate()
        assert "1 without token" in capsys.readouterr().out
        assert migrate_users.users_pk(job_storage.engine) == ["name"]
        # migration
        migrate_users.migrate(apply=True)
        assert migrate_users.users_pk(job_storage.engine) == ["name", "token"]
        assert self.rows(old_db, "SELECT name, roles FROM users ORDER BY name") == [("alice", "job1"), ("bob", "")]
        assert self.rows(old_db, "SELECT token FROM users WHERE name='bob'")[0][0]  # a random token was set
        assert self.rows(old_db, "SELECT owner_token FROM jobs") == [("alice-token",)]
        # the same name with another token is now another account
        storage.SQLAlchemyJobStorage().add_user("alice", token="other-token")
        assert self.rows(old_db, "SELECT count(*) FROM users WHERE name='alice'") == [(2,)]
        assert storage.SQLAlchemyJobStorage().has_role("alice", "alice-token", role="job1")
        assert not storage.SQLAlchemyJobStorage().has_role("alice", "other-token", role="job1")
        # nothing to do the second time
        capsys.readouterr()
        migrate_users.migrate(apply=True)
        assert "Already migrated" in capsys.readouterr().out


class TestMigrateEntities:

    @pytest.fixture
    def old_db(self, tmp_path, monkeypatch):
        """Server database with the entities table of previous versions (no owner_token)"""
        path = tmp_path / "old_entities.db"
        real_storage = storage.SQLAlchemyJobStorage
        monkeypatch.setattr(storage, "SQLAlchemyJobStorage", lambda: real_storage(db_string=f"sqlite:///{path}"))
        storage.SQLAlchemyJobStorage().engine.dispose()  # create the tables
        db = sqlite3.connect(path)
        db.executescript("""
            ALTER TABLE entities DROP COLUMN owner_token;
            INSERT INTO jobs (jobid, jobname, owner, owner_token, phase) VALUES
                ('j1', 'job1', 'alice', 'alice-token', 'COMPLETED'),
                ('j2', 'job1', 'alice', 'alice-token2', 'COMPLETED');
            INSERT INTO entities (entity_id, jobid, owner) VALUES
                ('generated', 'j1', 'alice'),  -- result of job j1
                ('uploaded', NULL, 'alice'),  -- file uploaded for job j2
                ('orphan', NULL, 'alice');
            INSERT INTO used (entity_id, jobid, owner) VALUES ('uploaded', 'j2', 'alice');
        """)
        db.commit()
        db.close()
        return path

    def test_migration(self, old_db, capsys):
        job_storage = storage.SQLAlchemyJobStorage()
        assert not migrate_users.entities_owner_token(job_storage.engine)
        # dry run
        migrate_users.migrate()
        assert "owner_token column missing" in capsys.readouterr().out
        assert not migrate_users.entities_owner_token(job_storage.engine)
        # migration (also done at the start of the server)
        assert migrate_users.migrate_entities(job_storage)
        with sqlite3.connect(old_db) as db:
            tokens = dict(db.execute("SELECT entity_id, owner_token FROM entities").fetchall())
        assert tokens == {"generated": "alice-token", "uploaded": "alice-token2", "orphan": None}
        # nothing to do the second time
        assert not migrate_users.migrate_entities(job_storage)
        migrate_users.migrate(apply=True)
        assert "owner_token column present" in capsys.readouterr().out


class TestRotateTokens:

    def create_user(self, email, token):
        """Client account, and its account and job on the server"""
        with c.app.app_context():
            c.user_datastore.create_user(email=email, token=token, roles=["user"])
            c.db.session.commit()
        job_storage = storage.SQLAlchemyJobStorage()
        job_storage.add_user(email, token=token)
        with job_storage.get_session() as session:
            jobid = uuid.uuid4().hex[:8]
            session.add(job_storage.Job(jobid=jobid, jobname="job1", owner=email, owner_token=token, phase="COMPLETED"))
            session.add(job_storage.Entity(entity_id=uuid.uuid4().hex, jobid=jobid, owner=email, owner_token=token))
            session.commit()

    def tokens(self, email):
        """Token in the client, and tokens of the account and of the jobs (and their files) on the server"""
        with c.app.app_context():
            client_token = c.User.query.filter_by(email=email).one().token
        job_storage = storage.SQLAlchemyJobStorage()
        with job_storage.get_session() as session:
            server = {u.token for u in session.query(job_storage.User).filter_by(name=email)}
            jobs = {j.owner_token for j in session.query(job_storage.Job).filter_by(owner=email)}
            files = {e.owner_token for e in session.query(job_storage.Entity).filter_by(owner=email)}
        assert files == jobs
        return client_token, server, jobs

    def test_rotation(self, capsys):
        suffix = int(time.time() * 1000)
        predictable = f"predictable{suffix}@example.org"
        legacy = rotate_tokens.legacy_token(predictable, rotate_tokens.APP_PATH)
        custom = f"custom{suffix}@example.org"
        moved = f"moved{suffix}@example.org"
        legacy_moved = rotate_tokens.legacy_token(moved, "/previous/opus")
        self.create_user(predictable, legacy)
        self.create_user(custom, "custom-token")
        self.create_user(moved, legacy_moved)
        # dry run
        rotate_tokens.rotate()
        out = capsys.readouterr().out
        assert f"{predictable}: server user 1, server jobs 1, server files 1" in out and custom not in out and moved not in out
        assert self.tokens(predictable) == (legacy, {legacy}, {legacy})
        # replace the predictable tokens (also for another previous install path)
        rotate_tokens.rotate(apply=True, legacy_paths=[rotate_tokens.APP_PATH, "/previous/opus"])
        for email, old in [(predictable, legacy), (moved, legacy_moved)]:
            client_token, server, jobs = self.tokens(email)
            assert client_token != old and uuid.UUID(client_token).version == 4
            assert server == {client_token} and jobs == {client_token}  # the jobs are still owned
        assert self.tokens(custom) == ("custom-token", {"custom-token"}, {"custom-token"})
        # the admin token is never replaced
        with c.app.app_context():
            admin = c.User.query.filter_by(email=settings.ADMIN_NAME).one()
            assert admin.token == settings.ADMIN_TOKEN.get_secret_value()
        # all the tokens (except the admin token)
        rotate_tokens.rotate(apply=True, rotate_all=True)
        assert self.tokens(custom)[0] != "custom-token"
        with c.app.app_context():
            assert c.User.query.filter_by(email=settings.ADMIN_NAME).one().token == settings.ADMIN_TOKEN.get_secret_value()
