# -*- coding: utf-8 -*-

"""
reset_password.py

Script reset the password of a auth_user record.
"""
from __future__ import print_function
import getpass
import os
from optparse import OptionParser
from gluon import *
from gluon.shell import env
from gluon.validators import CRYPT
from applications.zcomx.modules.creators import AuthUser
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']


# line-too-long (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    reset_password.py [OPTIONS] email [password]

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

    --vv,
        More verbose. Print debug messages to stdout.

    -x EMAIL, --exclude=EMAIL
        Exclude the account with this email when updating users.
        Use with --all option.
    """)


def main():
    """Main processing."""

    usage = '%prog [options] email [password]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Update all accounts.',
    )
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
    parser.add_option(
        '-x', '--exclude',
        dest='exclude', default=None,
        help='Exclude this account from update.',
    )

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    emails = []
    passwd = None
    if options.all:
        if len(args) > 1:
            print(parser.print_help())
            exit(1)
        emails = [x.email for x in db(db.auth_user).select(db.auth_user.email)]
        if len(args) == 1:
            passwd = args[0]
    else:
        if not args or len(args) > 2:
            print(parser.print_help())
            exit(1)
        emails = [args[0]]
        if len(args) == 2:
            passwd = args[1]

    if not passwd:
        passwd = getpass.getpass()

    for email in emails:
        if options.exclude and options.exclude == email:
            continue
        LOG.debug('Updating: %s', email)
        auth_user = AuthUser.from_key(dict(email=email))
        alg = 'pbkdf2(1000,20,sha512)'
        passkey = str(CRYPT(digest_alg=alg, salt=True)(passwd)[0])

        data = {
            'password': passkey,
            'registration_key': '',
            'reset_password_key': ''
        }
        AuthUser.from_updated(auth_user, data)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
