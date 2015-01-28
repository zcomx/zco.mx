#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
update_creator_indicia.py

Script to update a creator's indicia.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import datetime
import logging
from optparse import OptionParser
from applications.zcomx.modules.indicias import \
    clear_creator_indicia, \
    create_creator_indicia
from applications.zcomx.modules.utils import entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def modified(min_age, creator_id=None):
    """Return a list of creator ids whose indicia images were modified.

    Args:
        min_age: minimum age of modification
        creator_id: integer, only check this creator_id

    Returns:
        list of ids
    """
    ids = []
    query = (db.creator.indicia_modified != None)
    if creator_id is not None:
        query = query & (db.creator.id == creator_id)
    rows = db(query).select()
    for r in rows:
        age = (datetime.datetime.now() - r.indicia_modified).total_seconds()
        if age >= min_age:
            ids.append(r.id)
    return ids


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
    update_creator_indicia.py --modified 3600
                                # Create indicia for all creators
                                # where indicia_modified over an hour ago

OPTIONS
    -c, --clear
        Clear indicia images and exit. Remove all sizes of images related to
        creator fields: indicia_image, indicia_portrait, indicia_landscape.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -m AGE, --modified=AGE
        Update all creators where the indicia image was modified. The
        indicia_modified field has to be set and at least AGE seconds old.

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
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Clear creator indicia fields and exit.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-m', '--modified', type='int',
        dest='modified', default=None,
        help='Optimize the images.',
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

    if options.modified is None and len(args) < 1:
        parser.print_help()
        exit(1)

    ids = []
    record_id = None
    if args:
        try:
            record_id = int(args[0])
        except (TypeError, ValueError):
            record_id = 0

        if not record_id:
            print 'No creator found, id: {i}'.format(i=args[0])
            quit(1)

    if options.modified is not None:
        ids = modified(options.modified, creator_id=record_id)
    else:
        ids = [record_id]

    for creator_id in ids:
        creator = entity_to_row(db.creator, creator_id)
        if not creator:
            print 'No creator found, id: {i}'.format(i=record_id)
            quit(1)

        LOG.debug('Updating creator.path_name: %s', creator.path_name)

        if options.clear:
            clear_creator_indicia(creator)
        else:
            create_creator_indicia(
                creator,
                resize=options.resize,
                optimize=options.optimize
            )
        creator.update_record(indicia_modified=None)
        db.commit()


if __name__ == '__main__':
    main()