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

# C0301 (line-too-long): *Line too long (%%s/%%s)*
# pylint: disable=C0301


def clear(client):
    """Delete existing posts.

    Args:
        client: pytumblr TumblrRestClient instance
    """
    posts_response = client.posts('zcomx')
    for post in posts_response['posts']:
        LOG.debug('Deleting: %s', post['id'])
        client.delete_post('zcomx', post['id'])


def create_photo(client):
    """POC tumblr API create_photo."""
    photo_data = dict(
        state="private",
        tags=['tag1', 'tag2', 'zco.mx'],
        format='html',
        slug='unique-slug-002',
        source='https://zco.mx/images/download/book_page.image.b224f4ba0b8dff48.757074696768742d3030312d30312e706e67.png?size=web',
        link='https://zco.mx',
        caption='This is a test',
    )

    # photo['source'] = 'https://zco.mx/zcomx/static/images/zco.mx-logo-small.png'
    photo_data['caption'] = """
<h3><a href="https://zco.mx/JordanCrane/Uptight-001">Uptight 001 (2006)</a></h3><p>Test 001</p><p>by <a class="orange" id="test" href="https://zco.mx/JordanCrane">https://zco.mx/JordanCrane</a> |<a href="http://whatthingsdo.com">website</a> | <a href="https://twitter.com/Jordan_Crane">twitter</a> | <a href="https://whatthingsdo.tumblr.com">tumblr</a></p>
"""
    # """       # fixes vim syntax highlighting.
    result = client.create_photo('zcomx', **photo_data)
    print 'create_photo: {id}'.format(id=result)


def create_quote(client):
    """POC tumblr API create_quote."""
    quote_data = dict(
        state="private",
        tags=['Uptight', 'JordanCrane', 'zco.mx'],
        format='html',
        slug='Jordan Crane Uptight-001',
        quote='This is the quote of the day',
        source='Joe Doe',
    )
    result = client.create_quote('zcomx', **quote_data)
    print 'create_quote: {q}'.format(q=result)


def create_text(client):
    """POC tumblr API create_text."""
    text_data = dict(
        state="private",
        tags=['Uptight', 'JordanCrane', 'zco.mx'],
        format='html',
        slug='Jordan Crane Uptight-001',
        title='<span style="font-size: 18px;">List of Updated Ongoing Books for Thu, May 28, 2015</span>',
        body="""
         <ul>
            <li> Name of Book by <tumblr_nick> - page <15>, <16>, <17></li>
            <li> Book Title by <tumblr_nick> - page <57></li>
            <li> Eavesdropper 001 by <andreatsurumi> - page <14></li>
        </ul>
        """,
    )
    result = client.create_text('zcomx', **text_data)
    print 'create_text: {r}'.format(r=result)


def delete_post(client, post_id):
    """POC tumblr API delete_post."""
    result = client.delete_post('zcomx', post_id)
    print 'client.delete_post: {r}'.format(r=result)


def info(client):
    """Get client info results."""
    print 'client.info: {i}'.format(i=client.info())


def posts(client, hostname='zcomx'):
    """Get client posts results."""
    print 'client.posts: {p}'.format(p=client.posts(hostname))


def posts_summary(client, hostname='zcomx'):
    """Get client posts results."""
    results = client.posts(hostname)
    if 'posts' not in results:
        LOG.error('posts not found in results')
        return

    for post in results['posts']:
        print '{id} {slug}'.format(id=post['id'], slug=post['slug'])


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

    usage = '%prog [options] [post_id]'
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

    if args:
        post_id = args[0]

    LOG.info('Started.')
    LOG.debug('post_id: %s', post_id)

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

    info(client)
    # posts(client)
    # posts(client, hostname='charlesforsman')
    # posts_summary(client)
    # delete_post(client, post_id)
    # create_photo(client)
    # create_quote(client)
    # create_text(client)
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
