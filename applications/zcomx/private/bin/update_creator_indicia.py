#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
update_creator_indicia.py

Script to update a creator's indicia.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.images import store
from applications.zcomx.modules.indicias import CreatorIndiciaPagePng
from applications.zcomx.modules.utils import entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def create_indicia(creator, options):
    """Create indicia for creator.

    Args:
        creator: Row instance representing creator.
        options: dict of OptionParser options

    """
    LOG.debug('Creating indicia for: %s', creator.path_name)
    data = {}
    for orientation in ['portrait', 'landscape']:
        LOG.debug('Creating %s indicia', orientation)
        png_page = CreatorIndiciaPagePng(creator)
        png = png_page.create(orientation=orientation)
        field = 'indicia_{o}'.format(o=orientation)
        stored_filename = store(
            db.creator[field],
            png,
            resize=options.resize,
            run_optimize=options.optimize,
        )
        LOG.debug('stored_filename: %s', stored_filename)
        if stored_filename:
            data[field] = stored_filename

    data['indicia_start'] = None            # Clear in-progress status
    if data:
        creator.update_record(**data)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print """
Portrait and landscape versions of the indicia image are created, resized
and stored in uploads subdirectories. These fields are updated.
    creator.indicia_portrait
    creator.indicia_landscape

USAGE
    update_creator_indicia.py [OPTIONS] id

    update_creator_indicia.py 101       # Create indicia for creator, id=101

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -o, --optimize
        Optimize images. This takes longer.

    -r, --resize
        Create resized versions of images. This takes longer.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] creator_id'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-o', '--optimize',
        action='store_true', dest='optimize', default=False,
        help='Optimize the images.',
    )
    parser.add_option(
        '-r', '--resize',
        action='store_true', dest='resize', default=False,
        help='Create different sizes of the images.',
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

    if len(args) < 1:
        parser.print_help()
        exit(1)

    record_id = None
    try:
        record_id = int(args[0])
    except (TypeError, ValueError):
        record_id = 0

    if not record_id:
        print 'No creator found, id: {i}'.format(i=args[0])
        quit(1)

    record = entity_to_row(db.creator, record_id)
    if not record:
        print 'No creator found, id: {i}'.format(i=record_id)
        quit(1)

    create_indicia(record, options)


if __name__ == '__main__':
    main()
