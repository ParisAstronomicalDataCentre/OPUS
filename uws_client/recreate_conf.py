#!/usr/bin/env python

from datetime import datetime
from cork import Cork


def populate_conf_directory():
    cork = Cork('cork_conf', initialize=True)

    cork._store.roles['admin'] = 100
    cork._store.roles['user'] = 50
    cork._store.save_roles()

    tstamp = str(datetime.utcnow())

    username = 'admin'
    password = 'cta'
    cork._store.users[username] = {
        'role': 'admin',
        'hash': cork._hash(username, password),
        'email_addr': '@localhost.local',
        'creation_date': tstamp
    }

    username = 'user'
    password = 'cta'
    cork._store.users[username] = {
        'role': 'user',
        'hash': cork._hash(username, password),
        'email_addr': username + '@localhost.local',
        'creation_date': tstamp
    }

    cork._store.save_users()


if __name__ == '__main__':
    populate_conf_directory()

