#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
tumblr_poc.py

Script to POC test using pytumblr api.
https://pypi.python.org/pypi/PyTumblr
"""
import logging
import sys
import traceback
import pytumblr
from gluon import *
from optparse import OptionParser

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def clear(client):
    """Delete existing posts.

    Args:
        client: pytumblr TumblrRestClient instance
    """
    posts_response = client.posts('zcomx')
    for post in posts_response['posts']:
        LOG.debug('Deleting: %s', post['id'])
        client.delete_post('zcomx', post['id'])


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    tumblr_poc.py

OPTIONS
    -c, --clear
        Delete all existing posts.

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
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Delete existing posts.',
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

    # Authenticate via OAuth
    settings = current.app.local_settings

    client = pytumblr.TumblrRestClient(
        settings.tumblr_consumer_key,
        settings.tumblr_consumer_secret,
        settings.tumblr_oauth_token,
        settings.tumblr_oauth_secret
    )

    if options.clear:
        clear(client)
        return

    # Make the request
    x = client.info()
    print 'x: {var}'.format(var=x)
    # x = client.posts('zcomx')
    # x = client.delete_post('zcomx', '116050875376')
#     client.create_photo(
#         'zcomx',
#         state="private",
#         tags=['Uptight', 'JordanCrane', 'zco.mx'],
#         tweet='Uptight 001|Jordan Crane|https://zco.mx/JordanCrane/Uptight-001',
#         format='markdown',
#         slug='Jordan Crane Uptight-001',
#         source='https://zco.mx/images/download/book_page.image.b224f4ba0b8dff48.757074696768742d3030312d30312e706e67.png?size=web',
#         link="https://zco.mx/JordanCrane/Uptight-001",
#         caption="""
# ###<a href="https://zco.mx/JordanCrane/Uptight-001">Uptight 001 (2006)</a>###
#
# Test 001
#
# by <a class="orange" id="test" href="https://zco.mx/JordanCrane">https://zco.mx/JordanCrane</a>
# | <a href="http://whatthingsdo.com">website</a>
# | <a href="https://twitter.com/Jordan_Crane">twitter</a>
# | <a href="https://whatthingsdo.tumblr.com">tumblr</a>
# """,
#     )

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
