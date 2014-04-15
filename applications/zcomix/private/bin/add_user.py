#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
add_user.py

Script to create a user account from the cli.
"""
import datetime
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def create_user(info):
    """Create a user from the provided info.

    Args:
        info: dict, {'name': name, 'email': email, 'password': pw }
    """
    LOG.info('Creating user: {name}'.format(name=info['name']))
    # Create auth_user record
    auth = APP_ENV['auth']
    user = auth.get_or_create_user(info)
    if user and user.id:
        LOG.info('User created, id: {uid}'.format(uid=user.id))
    else:
        LOG.error('Function for creating user not returning a value.')
        LOG.error('Create user failed.')
        LOG.error('Check with admin.')


def get_user_info():
    """Prompt for the user info."""
    info = {
        'name': '',
        'email': '',
        'password': '',
    }
    print 'Enter the user info. Leave name blank to exit.'
    for k in ['name', 'email', 'password']:
        while True:
            raw_value = raw_input('{t}: '.format(t=k.title()))
            if k == 'name' and not raw_value:
                return info
            requires = db.auth_user[k].requires
            error_msg = ''
            if requires:
                if not isinstance(requires, (list, tuple)):
                    requires = [requires]
                for validator in requires:
                    (info[k], errors) = validator(raw_value)
                    if not errors is None:
                        error_msg = errors
                        break
            if error_msg:
                print 'ERROR: ', error_msg
            else:
                break
    return info


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    add_user.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        for h in LOG.handlers:
            if h.__class__ == logging.StreamHandler:
                h.setLevel(level)

    LOG.info('Started.')
    while True:
        info = get_user_info()
        if not info['name']:
            break
        create_user(info)
        print
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
