#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_creator_indicia.py

Script to update a creator's indicia.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='update_creator_indicia.py')

    parser.add_argument(
        'creator_ids',
        metavar='creator_id [creator_id ...]'
    )

    parser.add_argument(
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Clear creator indicia fields and exit.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-o', '--optimize',
        action='store_true', dest='optimize', default=False,
        help='Optimize the images.',
    )
    parser.add_argument(
        '-r', '--resize',
        action='store_true', dest='resize', default=False,
        help='Create different sizes of the images.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    ids = []
    for raw_record_id in args.creator_ids:
        try:
            record_id = int(raw_record_id)
        except (TypeError, ValueError):
            print('Invalid creator id: {i}'.format(i=raw_record_id))
            sys.exit(1)
        ids.append(record_id)

    for creator_id in ids:
        try:
            creator = Creator.from_id(creator_id)
        except LookupError:
            print('No creator found, id: {i}'.format(i=record_id))
            sys.exit(1)

        LOG.debug('Updating creator: %s', creator.name_for_url)

        if args.clear:
            clear_creator_indicia(creator)
        else:
            create_creator_indicia(
                creator,
                resize=args.resize,
                optimize=args.optimize
            )


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
