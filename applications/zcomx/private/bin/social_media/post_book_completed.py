#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
post_book_completed.py

Script to post a completed book on social media (eg facebook, tumblr and
twitter).
"""
from __future__ import print_function
import sys
import traceback
from optparse import OptionParser
from gluon import *
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.social_media import \
    SocialMediaPostError, \
    SocialMediaPoster
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    post_book_completed.py [OPTIONS] book_id               # Post book

OPTIONS
    -f, --force
        Post regardless if book record indicates a post has already been
        made (ie book.tumblr_post_id and book.twitter_post_id are set)

    --facebook
        Post only on facebook.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    --tumblr
        Post only on tumblr.

    --twitter
        Post only on twitter.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options] book_id'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Post regardles if book post_ids exist.',
    )
    parser.add_option(
        '--facebook',
        action='store_true', dest='facebook', default=False,
        help='Post only on facebook.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '--tumblr',
        action='store_true', dest='tumblr', default=False,
        help='Post only on tumblr.',
    )
    parser.add_option(
        '--twitter',
        action='store_true', dest='twitter', default=False,
        help='Post only on twitter.',
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

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')
    book_id = args[0]

    book = Book.from_id(book_id)
    creator = Creator.from_id(book.creator_id)

    services = []
    if options.facebook:
        services.append('facebook')
    if options.tumblr:
        services.append('tumblr')
    if options.twitter:
        services.append('twitter')
    if not options.facebook and not options.tumblr and not options.twitter:
        services = ['facebook', 'tumblr', 'twitter']

    for social_media_service in services:
        LOG.debug('Posting to: %s', social_media_service)
        poster = SocialMediaPoster.class_factory(social_media_service)
        try:
            post_id = poster.post(book, creator)
        except SocialMediaPostError as err:
            post_id = None
            LOG.error(
                'Social media post (%s) failed for book: %s - %s',
                social_media_service,
                book.id,
                book.name
            )
            if err:
                LOG.error(err)

        if post_id:
            field = '{s}_post_id'.format(s=social_media_service)
            data = {field: post_id}
            book = Book.from_updated(book, data)

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
