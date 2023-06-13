#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
add_user.py

Script to create a user account from the cli.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


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
    print('Enter the user info. Leave name blank to exit.')
    for k in ['name', 'email', 'password']:
        while True:
            raw_value = input('{t}: '.format(t=k.title()))
            if k == 'name' and not raw_value:
                return info
            requires = db.auth_user[k].requires
            error_msg = ''
            if requires:
                if not isinstance(requires, (list, tuple)):
                    requires = [requires]
                for validator in requires:
                    (info[k], errors) = validator(raw_value)
                    if errors is not None:
                        error_msg = errors
                        break
            if error_msg:
                print('ERROR: ', error_msg)
            else:
                break
    return info


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    add_user.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='add_user.py')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    LOG.info('Started.')
    while True:
        info = get_user_info()
        if not info['name']:
            break
        create_user(info)
        print('')
    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
