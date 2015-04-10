#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
twitter_poc.py

Script to POC test using python-twitter api.
https://pypi.python.org/pypi/twitter
"""
import logging
import sys
import traceback
from optparse import OptionParser
from twitter import Twitter
from twitter.oauth import OAuth

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    twitter_poc.py

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
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    LOG.info('Started.')

    TOKEN = '262332119-7bclllngLikvfVFAqgSe1cRNUE0cnVSYD2YOX7Ju'
    TOKEN_KEY = 'aRTJHmcY6szoRLCfHZccTkCqX7yrL3B4fYjwB5ZrI'
    CONSUMER_KEY = 'uS6hO2sV6tDKIOeVjhnFnQ'
    CONSUMER_SECRET = 'MEYTOS97VvlHX7K1rwHPEqVpTSqZ71HtvoK4sVuYk'

    token = TOKEN
    token_key = TOKEN_KEY
    con_secret = CONSUMER_KEY
    con_secret_key = CONSUMER_SECRET

    t = Twitter(
        auth=OAuth(token, token_key, con_secret, con_secret_key)
    )
    # x = t.statuses.home_timeline()
    # x = t.account.settings()
    # x = t.statuses.user_timeline(screen_name="CharlesForsman", count=1)
    # x = t.search.tweets(q="sittler", count=2)
    # x = t.statuses.update(status='Testing')
    # x = t.statuses.update(status='Development test http://zco.mx')
    x = t.statuses.destroy(id='586561746363621377')

    print 'x: {var}'.format(var=x)
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
