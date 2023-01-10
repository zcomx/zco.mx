#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tumblr2_api.py

Script to test using pytumblr2 api.
https://pypi.python.org/pypi/PyTumblr2
"""
import sys
import traceback
from optparse import OptionParser
import pytumblr2
from gluon import *
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'

# C0301 (line-too-long): *Line too long (%%s/%%s)*
# pylint: disable=C0301


def clear(client):
    """Delete existing posts.

    Args:
        client: pytumblr2 TumblrRestClient instance
    """
    posts_response = client.posts('zcomx')
    for post in posts_response['posts']:
        LOG.debug('Deleting: %s', post['id'])
        client.delete_post('zcomx', post['id'])


def delete_post(client, post_id):
    """tumblr API delete_post."""
    result = client.delete_post('zcomx', post_id)
    print('client.delete_post: {r}'.format(r=result))


def info(client):
    """Get client info results."""
    print('client.info: {i}'.format(i=client.info()))


def legacy_create_photo(client):
    """tumblr API legacy_create_photo."""
    photo_data = dict(
        state="draft",
        tags=['tag1', 'tag2', 'zco.mx'],
        format='html',
        slug='unique-slug-002',
        source='https://zco.mx/images/download/book_page.image.b224f4ba0b8dff48.757074696768742d3030312d30312e706e67.png?size=web',
        link='https://zco.mx',
        caption='This is a test',
        tweet=None,
    )

    # photo['source'] = 'https://zco.mx/zcomx/static/images/zco.mx-logo-small.png'
    photo_data['caption'] = """
<h3><a href="https://zco.mx/JordanCrane/Uptight-001">Uptight 001 (2006)</a></h3><p>Test 001</p><p>by <a class="orange" id="test" href="https://zco.mx/JordanCrane">https://zco.mx/JordanCrane</a> |<a href="http://whatthingsdo.com">website</a> | <a href="https://twitter.com/Jordan_Crane">twitter</a> | <a href="https://whatthingsdo.tumblr.com">tumblr</a></p>
"""
    # """       # fixes vim syntax highlighting.
    result = client.legacy_create_photo('zcomx', **photo_data)
    print('legacy_create_photo: {id}'.format(id=result))


def legacy_create_quote(client):
    """tumblr API legacy_create_quote."""
    quote_data = dict(
        state="private",
        tags=['Uptight', 'JordanCrane', 'zco.mx'],
        format='html',
        slug='Jordan Crane Uptight-001',
        quote='This is the quote of the day',
        source='Joe Doe',
    )
    result = client.legacy_create_quote('zcomx', **quote_data)
    print('legacy_create_quote: {q}'.format(q=result))


def legacy_create_text(client):
    """tumblr API legacy_create_text."""
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
    result = client.legacy_create_text('zcomx', **text_data)
    print('legacy_create_text: {r}'.format(r=result))


def posts(client, hostname='zcomx'):
    """Get client posts results."""
    print('client.posts: {p}'.format(p=client.posts(hostname)))


def posts_summary(client, hostname='zcomx'):
    """Get client posts results."""
    results = client.posts(hostname)
    if 'posts' not in results:
        LOG.error('posts not found in results')
        return

    for post in results['posts']:
        print('{id} {slug}'.format(id=post['id'], slug=post['slug']))


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    tumblr_api.py

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

    """)


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

    set_cli_logging(LOG, options.verbose, options.vv)

    post_id = None
    if args:
        post_id = args[0]

    LOG.info('Started.')
    LOG.debug('post_id: %s', post_id)

    # Authenticate via OAuth
    settings = current.app.local_settings

    client = pytumblr2.TumblrRestClient(
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
    # legacy_create_photo(client)
    # legacy_create_quote(client)
    # legacy_create_text(client)
    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
