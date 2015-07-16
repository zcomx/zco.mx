#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
post_book_completed.py

Script to post a completed book on social media (eg tumblr and twitter).
"""
import logging
from gluon import *
from optparse import OptionParser
from applications.zcomx.modules.social_media import \
    POSTER_CLASSES, \
    SocialMediaPostError
from applications.zcomx.modules.utils import \
    entity_to_row


VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    post_book_completed.py [OPTIONS] book_id               # Post book

OPTIONS
    -f, --force
        Post regardless if book record indicates a post has already been
        made (ie book.tumblr_post_id and book.twitter_post_id are set)

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
    """


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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')
    book_id = args[0]

    book = entity_to_row(db.book, book_id)
    if not book:
        raise LookupError('Book not found, id: %s', book_id)

    creator = entity_to_row(db.creator, book.creator_id)
    if not creator:
        raise LookupError('Creator not found, id: %s', book.creator_id)

    services = []
    if options.tumblr:
        services.append('tumblr')
    if options.twitter:
        services.append('twitter')
    if not options.tumblr and not options.twitter:
        services = ['tumblr', 'twitter']

    for service in services:
        poster_class = POSTER_CLASSES[service]
        try:
            post_id = poster_class().post(book, creator)
        except SocialMediaPostError as err:
            post_id = None
            LOG.error(
                'Social media post (%s) failed for book: %s - %s',
                service,
                book.id,
                book.name
            )
            if err:
                LOG.error(err)

        if post_id:
            field = '{s}_post_id'.format(s=service)
            data = {field: post_id}
            book.update_record(**data)
            db.commit()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
