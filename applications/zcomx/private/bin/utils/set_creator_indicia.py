#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
set_creator_indicia.py

Script to set the creator indicia image.
This is used for testing.
* Stores the image in the uploads directory
* Sets the creator.indicia_image field.
The update_creator_indicia is not queued.
"""
import argparse
import os
import shutil
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images import (
    ResizeImgIndicia,
    store,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    set_creator_indicia.py [OPTIONS] id|name file.png

    set_creator_indicia.py 101 file.png                   # Set indicia by id
    set_creator_indicia.py 'Charles Forsman' file.png     # Set indicia by name

OPTIONS

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='set_creator_indicia.py')

    parser.add_argument('name', metavar='id|name')
    parser.add_argument('image_fullname')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
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

    record_id = None
    name = None
    try:
        record_id = int(args.name)
    except (TypeError, ValueError):
        name = args.name

    if record_id is None:
        query = (db.auth_user.name == name)
        rows = db(query).select(
            left=db.creator.on(
                db.creator.auth_user_id == db.auth_user.id),
        )
        if not rows:
            print('No creator found, name: {n}'.format(n=name))
            sys.exit(1)
        if len(rows) > 1:
            print('Multiple creator matches, use creator id:')
            for r in rows:
                print('id: {i}'.format(i=r.id))
            sys.exit(1)
        record_id = rows[0].creator.id

    creator = None
    try:
        creator = Creator.from_id(record_id)
    except LookupError:
        pass

    if creator is None:
        LOG.error('Creator not found: %s', args.name)
        return

    image_fullname = args.image_fullname

    if not os.path.exists(image_fullname):
        print('File not found: {n}'.format(n=image_fullname))
        sys.exit(1)

    # Cp the file to a tmp directory so it is not deleted.
    tmp_dir = '/tmp/set_creator_indicia'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    local_filename = os.path.join(tmp_dir, os.path.basename(image_fullname))

    # Copy file name so original is not touched
    shutil.copy(image_fullname, local_filename)

    LOG.debug('Storing image')
    img_field = 'indicia_image'
    # This code copied/adapted from controllers/login.py def
    # creator_img_handler.
    resizer = ResizeImgIndicia if img_field == 'indicia_image' else None
    # pylint: disable=broad-except
    try:
        stored_filename = store(
            db.creator[img_field], local_filename, resizer=resizer)
    except Exception as err:
        print(
            'Creator image upload error: {err}'.format(err=err),
            file=sys.stderr
        )
        stored_filename = None

    if not stored_filename:
        print(
            'Stored filename not returned. Aborting.',
            file=sys.stderr
        )
        sys.exit(1)

    LOG.debug('stored_filename: %s', stored_filename)
    LOG.debug('Updating creator.indicia_image')
    data = {img_field: stored_filename}
    creator = Creator.from_updated(creator, data)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
