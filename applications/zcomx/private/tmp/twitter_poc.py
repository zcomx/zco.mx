#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
twitter_poc.py

Script to POC test using python-twitter api.
https://pypi.python.org/pypi/twitter
"""
import logging
import os
import pprint
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

    settings = current.app.local_settings

    client = Twitter(
        auth=OAuth(
            settings.twitter_oauth_token,
            settings.twitter_oauth_secret,
            settings.twitter_consumer_key,
            settings.twitter_consumer_secret
        )
    )
    x = client.statuses.home_timeline()
    # x = client.account.settings()
    # x = client.statuses.user_timeline(screen_name="CharlesForsman", count=1)
    # x = client.search.tweets(q="sittler", count=2)
    # x = client.statuses.update(status='Testing')
    # x = client.statuses.update(status='Development test http://zco.mx')
    # x = client.statuses.destroy(id='586561746363621377')
    # x = client.statuses.destroy(id='588821301546090498')
    # x = client.statuses.destroy(id='589138730570665984')
    # x = client.statuses.destroy(id='589139718580871169')
    # print 'x: {var}'.format(var=x)
    pprint.pprint(x)

    # Post tweet with image
    # status = "This is a test 010."
    # img = '/srv/http/jimk.zsw.ca/web2py/applications/zcomx/uploads/web/book_page.image/88/book_page.image.883f5a1fce8dced9.30315f31337468666c6f6f725f636f7665722e706e67.png'
    # print 'FIXME img: {var}'.format(var=img)
    # if not os.path.exists(img):
    #     print 'FIXME img not found: {var}'.format(var=img)
    #     exit(1)

    # with open(img, "rb") as imagefile:
    #     params = {"media[]": imagefile.read(), "status": status}
    #     x = client.statuses.update_with_media(**params)
    #     pprint.pprint(x)

    LOG.info('Done.')

if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
