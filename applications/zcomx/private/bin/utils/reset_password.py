# -*- coding: utf-8 -*-
"""
reset_password.py

Script reset the password of a auth_user record.
"""
import argparse
import getpass
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from gluon.validators import CRYPT
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.creators import AuthUser
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    reset_password.py [OPTIONS] email [password]
    reset_password.py email [password]
    reset_password.py --all [password]

    If the password is not provided, the user is prompted for it.

    WARNING: This script does what it says it does: it resets the passwords
    of users accounts. It is intended to be used in test environments. Use
    at own risk.

OPTIONS
    -a, --all
        Update all users.

    -h, --help
        Print a brief help.

    --man
        Print extended help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    -x EMAIL, --exclude=EMAIL
        Exclude the account with this email when updating users.
        Use with --all option.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='reset_password.py')

    parser.add_argument(
        'user_pws',
        nargs='*',
        default=[],
        metavar='email [password] | --all [password]',
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Update all accounts.',
    )
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
    parser.add_argument(
        '-x', '--exclude',
        dest='exclude', default=None,
        help='Exclude this account from update.',
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    emails = []
    passwd = None

    if args.all:
        if len(args.user_pws) > 1:
            parser.print_help()
            sys.exit(1)
        emails = [x.email for x in db(db.auth_user).select(db.auth_user.email)]
        if len(args.user_pws) == 1:
            passwd = args.user_pws[0]
    else:
        if not args.user_pws or len(args.user_pws) > 2:
            parser.print_help()
            sys.exit(1)
        emails = [args.user_pws[0]]
        if len(args.user_pws) == 2:
            passwd = args.user_pws[1]

    if not passwd:
        passwd = getpass.getpass()

    for email in emails:
        if args.exclude and args.exclude == email:
            continue
        LOG.debug('Updating: %s', email)
        try:
            auth_user = AuthUser.from_key(dict(email=email))
        except LookupError as err:
            LOG.error('Email not found: {e}'.format(e=email))
            continue
        alg = 'pbkdf2(1000,20,sha512)'
        passkey = str(CRYPT(digest_alg=alg, salt=True)(passwd)[0])

        data = {
            'password': passkey,
            'registration_key': '',
            'reset_password_key': ''
        }
        AuthUser.from_updated(auth_user, data)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
