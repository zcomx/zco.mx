#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
update_creator_indicia.py

Script to update a creator's indicia.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
from __future__ import print_function
from optparse import OptionParser
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images import on_delete_image
from applications.zcomx.modules.indicias import create_creator_indicia
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def clear_creator_indicia(creator):
    """Clear indicia for creator.

    Args:
        creator: Creator instance
    Returns:
        creator
    """
    fields = ['indicia_image', 'indicia_portrait', 'indicia_landscape']

    data = {}
    for field in fields:
        if creator[field]:
            on_delete_image(creator[field])
            data[field] = None

    creator = Creator.from_updated(creator, data)


def man_page():
    """Print manual page-like help"""
    print("""
Portrait and landscape versions of the indicia image are created, resized
and stored in uploads subdirectories. These fields are updated.
    creator.indicia_portrait
    creator.indicia_landscape

USAGE
    update_creator_indicia.py [OPTIONS] id [id2 id3 ...]

    update_creator_indicia.py 101       # Create indicia for creator, id=101

OPTIONS
    -c, --clear
        Clear indicia images and exit. Remove all sizes of images related to
        creator fields: indicia_image, indicia_portrait, indicia_landscape.

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
    """)


def main():
    """Main processing."""

    usage = '%prog [options] creator_id [creator_id_2 creator_id_3 ...]'
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) < 1:
        parser.print_help()
        exit(1)

    ids = []
    for arg in args:
        try:
            record_id = int(arg)
        except (TypeError, ValueError):
            print('Invalid creator id: {i}'.format(i=arg))
            quit(1)
        ids.append(record_id)

    for creator_id in ids:
        try:
            creator = Creator.from_id(creator_id)
        except LookupError:
            print('No creator found, id: {i}'.format(i=record_id))
            quit(1)

        LOG.debug('Updating creator: %s', creator.name_for_url)

        if options.clear:
            clear_creator_indicia(creator)
        else:
            create_creator_indicia(
                creator,
                resize=options.resize,
                optimize=options.optimize
            )


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
