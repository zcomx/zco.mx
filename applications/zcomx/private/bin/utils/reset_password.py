#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
reset_password.py

Script reset the password of a auth_user record.
"""
import getpass
import logging
import os
from gluon import *
from gluon.shell import env
from gluon.validators import CRYPT
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')

# line-too-long (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    reset_password.py [OPTIONS] email [password]

    If the password is not provided, the user is prompted for it.

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print extended help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """


def main():
    """Main processing."""

    usage = '%prog [options] email [password]'
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

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if not args or len(args) > 2:
        print parser.print_help()
        exit(1)

    email = args[0]
    user = db(db.auth_user.email == email).select().first()
    if not user:
        raise LookupError('User not found, email: {e}'.format(e=email))

    if len(args) == 1:
        passwd = getpass.getpass()
    else:
        passwd = args[1]

    alg = 'pbkdf2(1000,20,sha512)'
    passkey = str(CRYPT(digest_alg=alg, salt=True)(passwd)[0])

    user.update_record(**{
        'password': passkey,
        'registration_key': '',
        'reset_password_key': ''
    })


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
