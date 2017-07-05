#!/usr/bin/env python

import os
from datetime import datetime
from cork import Cork


def populate_conf_directory():

    if not os.path.isdir('cork_conf'):
        print('Creating cork_conf directory...')
        os.mkdir('cork_conf')

    cork = Cork('cork_conf', initialize=True)

    print('Add roles...')
    cork._store.roles['admin'] = 100
    cork._store.roles['user'] = 50
    cork._store.save_roles()

    tstamp = str(datetime.utcnow())

    print('Add user: admin...')
    username = 'admin'
    password = 'cta'
    cork._store.users[username] = {
        'role': 'admin',
        'hash': cork._hash(username, password),
        'email_addr': '@localhost.local',
        'creation_date': tstamp
    }

    print('Add user: user...')
    username = 'user'
    password = 'cta'
    cork._store.users[username] = {
        'role': 'user',
        'hash': cork._hash(username, password),
        'email_addr': username + '@localhost.local',
        'creation_date': tstamp
    }

    cork._store.save_users()

    print('Warning: cork_conf need to be writable by the web server, e.g. by running:\nsudo chown -R www cork_conf')
    print('Done')


if __name__ == '__main__':
    populate_conf_directory()

